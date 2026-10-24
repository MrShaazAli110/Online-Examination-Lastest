import os
import json
import csv
import io
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Response
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import engine, Base, get_db
from .models import User, Quiz, Question, Submission
from .auth import hash_password, verify_password, create_access_token, get_current_user, require_admin, require_admin_or_instructor
from .parsers import parse_uploaded_file, parse_questions_from_text
from .runner import run_all_test_cases, execute_single_case
from .seed_data import seed_database
from .supabase_sync import (
    sync_from_supabase,
    sync_quiz_to_supabase,
    delete_quiz_from_supabase,
    sync_question_to_supabase,
    delete_question_from_supabase,
    sync_user_to_supabase
)

# Create tables & seed default data safely
try:
    Base.metadata.create_all(bind=engine)
    seed_database()

except Exception as e:
    # In serverless environments, DB may already be initialized or momentarily connecting
    print(f"[Startup Notice] Database initialization: {e}")

app = FastAPI(
    title="Proctored Quiz & Coding Assessment Platform",
    description="Enterprise multi-tenant quiz and programming exam platform with strict anti-cheating proctoring.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- SCHEMAS -----------------
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    full_name: str
    role: str = "student"  # student, instructor, admin

class LoginRequest(BaseModel):
    username: str
    password: str

class QuizCreateRequest(BaseModel):
    title: str
    description: str = ""
    code: str
    duration_minutes: int = 30
    max_violations: int = 3

class QuizUpdateRequest(BaseModel):
    title: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    max_violations: Optional[int] = None
    is_active: Optional[bool] = None

class QuestionCreateRequest(BaseModel):
    question_type: str = "mcq"  # mcq, coding, short_answer
    title: str
    description: str = ""
    options: List[str] = []
    correct_answer: str = ""
    explanation: str = ""
    points: int = 5
    order_idx: int = 0
    starter_code: str = ""
    language: str = "python"
    test_cases: List[dict] = []

class CodeRunRequest(BaseModel):
    code: str
    language: str = "python"
    input_data: str = ""
    test_cases: List[dict] = []

class ViolationReportRequest(BaseModel):
    violation_type: str
    details: str = ""

class SaveProgressRequest(BaseModel):
    answers: dict = {}

# ----------------- AUTH ROUTES -----------------
@app.post("/api/auth/register")
def register_user(req: RegisterRequest, db: Session = Depends(get_db)):
    clean_username = req.username.strip().lower()
    clean_email = req.email.strip().lower()
    
    if db.query(User).filter(User.username == clean_username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == clean_email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    role = req.role if req.role in ["student", "instructor", "admin"] else "student"
    new_user = User(
        username=clean_username,
        email=clean_email,
        password_hash=hash_password(req.password),
        full_name=req.full_name.strip(),
        role=role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    sync_user_to_supabase(new_user)

    token = create_access_token(new_user.id, new_user.username, new_user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": new_user.to_dict()
    }

@app.post("/api/auth/login")
def login_user(req: LoginRequest, db: Session = Depends(get_db)):
    clean_username = req.username.strip().lower()
    user = db.query(User).filter(User.username == clean_username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    token = create_access_token(user.id, user.username, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user.to_dict()
    }

@app.get("/api/auth/me")
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return {"user": current_user.to_dict()}

# ----------------- QUIZ MANAGEMENT ROUTES -----------------
@app.get("/api/quizzes")
def list_quizzes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List quizzes. Students see active quizzes; Instructors/Admins see all with full stats."""
    is_staff = current_user.role in ["admin", "instructor"]
    
    # Auto-sync from Supabase if local DB has 0 quizzes (e.g. serverless cold start)
    if db.query(Quiz).count() == 0:
        sync_from_supabase(db)

    if is_staff:
        quizzes = db.query(Quiz).order_by(Quiz.created_at.desc()).all()
    else:
        quizzes = db.query(Quiz).filter(Quiz.is_active == True).order_by(Quiz.created_at.desc()).all()

    return {
        "quizzes": [q.to_dict(include_questions=False, is_admin_or_instructor=is_staff) for q in quizzes]
    }

@app.get("/api/quizzes/{quiz_id}")
def get_quiz_details(quiz_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    is_staff = current_user.role in ["admin", "instructor"]
    return quiz.to_dict(include_questions=True, is_admin_or_instructor=is_staff)

@app.post("/api/quizzes")
def create_quiz(req: QuizCreateRequest, current_user: User = Depends(require_admin_or_instructor), db: Session = Depends(get_db)):
    clean_code = req.code.strip().upper()
    existing = db.query(Quiz).filter(Quiz.code == clean_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Quiz code '{clean_code}' is already in use. Please choose a unique code.")

    quiz = Quiz(
        title=req.title.strip(),
        description=req.description.strip(),
        code=clean_code,
        instructor_id=current_user.id,
        duration_minutes=req.duration_minutes,
        max_violations=req.max_violations,
        is_active=True
    )
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    sync_quiz_to_supabase(quiz)
    return quiz.to_dict(include_questions=True, is_admin_or_instructor=True)

@app.put("/api/quizzes/{quiz_id}")
def update_quiz(quiz_id: int, req: QuizUpdateRequest, current_user: User = Depends(require_admin_or_instructor), db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    if req.code is not None and req.code.strip():
        new_code = req.code.strip().upper()
        if new_code != quiz.code:
            existing = db.query(Quiz).filter(Quiz.code == new_code, Quiz.id != quiz_id).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Quiz code '{new_code}' is already in use by another quiz.")
            quiz.code = new_code

    if req.title is not None and req.title.strip():
        quiz.title = req.title.strip()
    if req.description is not None:
        quiz.description = req.description.strip()
    if req.duration_minutes is not None:
        quiz.duration_minutes = req.duration_minutes
    if req.max_violations is not None:
        quiz.max_violations = req.max_violations
    if req.is_active is not None:
        quiz.is_active = req.is_active

    quiz.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(quiz)
    sync_quiz_to_supabase(quiz)
    return quiz.to_dict(include_questions=True, is_admin_or_instructor=True)

@app.delete("/api/quizzes/{quiz_id}")
def delete_quiz(quiz_id: int, current_user: User = Depends(require_admin_or_instructor), db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    # Cleanly remove all dependent records so foreign keys never fail
    db.query(Submission).filter(Submission.quiz_id == quiz_id).delete(synchronize_session=False)
    db.query(Question).filter(Question.quiz_id == quiz_id).delete(synchronize_session=False)
    db.delete(quiz)
    db.commit()

    # Synchronously delete from Supabase cloud database
    delete_quiz_from_supabase(quiz_id)
    return {"message": "Quiz deleted successfully"}

# ----------------- QUESTION MANAGEMENT ROUTES -----------------
@app.post("/api/quizzes/{quiz_id}/questions")
def add_question(quiz_id: int, req: QuestionCreateRequest, current_user: User = Depends(require_admin_or_instructor), db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    question = Question(
        quiz_id=quiz_id,
        question_type=req.question_type,
        title=req.title.strip(),
        description=req.description.strip(),
        correct_answer=req.correct_answer.strip().upper() if req.question_type == "mcq" else req.correct_answer.strip(),
        explanation=req.explanation.strip(),
        points=req.points,
        order_idx=req.order_idx or (len(quiz.questions) + 1),
        starter_code=req.starter_code,
        language=req.language,
    )
    question.set_options(req.options)
    question.set_test_cases(req.test_cases)

    db.add(question)
    db.commit()
    db.refresh(question)
    sync_question_to_supabase(question)
    return question.to_dict(include_solution=True)

@app.delete("/api/quizzes/{quiz_id}/questions/{question_id}")
def delete_question(quiz_id: int, question_id: int, current_user: User = Depends(require_admin_or_instructor), db: Session = Depends(get_db)):
    q = db.query(Question).filter(Question.id == question_id, Question.quiz_id == quiz_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    db.delete(q)
    db.commit()
    delete_question_from_supabase(question_id)
    return {"message": "Question deleted successfully"}


# ----------------- FILE UPLOAD & QUESTION PARSING -----------------
@app.post("/api/quizzes/parse-file-preview")
async def preview_uploaded_file(file: UploadFile = File(...), current_user: User = Depends(require_admin_or_instructor)):
    """Uploads a Word (.docx), PDF (.pdf), or Text (.txt) file and returns extracted questions for preview."""
    try:
        content = await file.read()
        questions = parse_uploaded_file(file.filename, content)
        return {
            "filename": file.filename,
            "question_count": len(questions),
            "questions": questions
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/quizzes/{quiz_id}/upload-questions")
async def upload_questions_file(
    quiz_id: int, 
    file: UploadFile = File(...), 
    current_user: User = Depends(require_admin_or_instructor), 
    db: Session = Depends(get_db)
):
    """Uploads file and directly appends parsed questions to the quiz."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if current_user.role != "admin" and quiz.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        content = await file.read()
        parsed_questions = parse_uploaded_file(file.filename, content)
        
        # If Supabase storage is configured, back up file in cloud bucket
        try:
            from .supabase_client import upload_to_supabase_storage
            upload_to_supabase_storage(file.filename, content, file.content_type or "application/octet-stream")
        except Exception:
            pass
        
        current_max_order = max([q.order_idx for q in quiz.questions], default=0)
        added_objs = []
        for i, q_data in enumerate(parsed_questions):
            q_obj = Question(
                quiz_id=quiz.id,
                question_type=q_data.get("question_type", "mcq"),
                title=q_data.get("title", f"Imported Question {i+1}"),
                description=q_data.get("description", ""),
                correct_answer=q_data.get("correct_answer", "A"),
                explanation=q_data.get("explanation", ""),
                points=q_data.get("points", 5),
                order_idx=current_max_order + i + 1,
                starter_code=q_data.get("starter_code", ""),
                language=q_data.get("language", "python")
            )
            q_obj.set_options(q_data.get("options", []))
            q_obj.set_test_cases(q_data.get("test_cases", []))
            db.add(q_obj)
            added_objs.append(q_obj)

        db.commit()
        return {
            "message": f"Successfully imported {len(added_objs)} questions from {file.filename}",
            "imported_count": len(added_objs)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ----------------- CODE RUNNER ROUTE -----------------
@app.post("/api/code/run-sample")
def run_sample_code(req: CodeRunRequest, current_user: User = Depends(get_current_user)):
    """Runs student code against sample / public test cases."""
    if not req.test_cases:
        # Run single test with custom input
        res = execute_single_case(req.code, req.input_data, "")
        return {
            "all_passed": res["passed"],
            "total": 1,
            "passed": 1 if res["status"] != "Runtime Error" else 0,
            "results": [res]
        }
    
    # Run against provided sample test cases (not hidden)
    sample_cases = [tc for tc in req.test_cases if not tc.get("is_hidden", False)]
    if not sample_cases:
        sample_cases = req.test_cases[:2]  # Fallback to first 2 if none marked
        
    return run_all_test_cases(req.code, sample_cases, run_hidden=False)

# ----------------- PROCTORED EXAM SESSIONS -----------------
@app.post("/api/quizzes/{quiz_id}/start")
def start_exam_session(quiz_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz or not quiz.is_active:
        raise HTTPException(status_code=404, detail="Active quiz not found")

    total_seconds = int(quiz.duration_minutes * 60)

    # Check for existing unfinished session
    existing = db.query(Submission).filter(
        Submission.quiz_id == quiz.id,
        Submission.user_id == current_user.id,
        Submission.is_completed == False
    ).first()

    if existing:
        sub = existing
        elapsed = int((datetime.utcnow() - sub.started_at).total_seconds())
        remaining_seconds = total_seconds - elapsed
        # If an existing session was stale or ran out of time previously, refresh it
        if remaining_seconds <= 0:
            sub.started_at = datetime.utcnow()
            sub.violation_count = 0
            sub.violation_logs_json = "[]"
            sub.answers_json = "{}"
            sub.coding_results_json = "{}"
            sub.status = "in_progress"
            sub.is_completed = False
            remaining_seconds = total_seconds
            db.commit()
            db.refresh(sub)
    else:
        sub = Submission(
            quiz_id=quiz.id,
            user_id=current_user.id,
            started_at=datetime.utcnow(),
            is_completed=False,
            status="in_progress",
            violation_count=0
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        remaining_seconds = total_seconds

    return {
        "submission_id": sub.id,
        "quiz": quiz.to_dict(include_questions=True, is_admin_or_instructor=False),
        "started_at": sub.started_at.isoformat() + "Z",
        "remaining_seconds": remaining_seconds,
        "duration_minutes": quiz.duration_minutes,
        "max_violations": quiz.max_violations,
        "current_violations": sub.violation_count,
        "saved_answers": sub.get_answers()
    }

@app.post("/api/submissions/{sub_id}/record-violation")
def record_proctoring_violation(
    sub_id: int, 
    req: ViolationReportRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    sub = db.query(Submission).filter(Submission.id == sub_id, Submission.user_id == current_user.id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission session not found")
    if sub.is_completed:
        return {
            "violation_count": sub.violation_count,
            "max_violations": sub.quiz.max_violations if sub.quiz else 3,
            "is_disqualified": True, 
            "message": "Exam has already concluded."
        }

    sub.add_violation(req.violation_type, req.details)
    db.commit()
    db.refresh(sub)

    max_allowed = sub.quiz.max_violations if sub.quiz else 3
    is_disqualified = (sub.violation_count >= max_allowed)

    return {
        "violation_count": sub.violation_count,
        "max_violations": max_allowed,
        "is_disqualified": is_disqualified,
        "message": f"Violation recorded: {req.violation_type} ({sub.violation_count}/{max_allowed})"
    }

@app.post("/api/submissions/{sub_id}/save-progress")
def save_exam_progress(
    sub_id: int, 
    req: SaveProgressRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    sub = db.query(Submission).filter(Submission.id == sub_id, Submission.user_id == current_user.id).first()
    if not sub or sub.is_completed:
        return {"status": "ignored"}

    current_answers = sub.get_answers()
    current_answers.update(req.answers)
    sub.set_answers(current_answers)
    db.commit()
    return {"status": "saved"}

@app.post("/api/submissions/{sub_id}/submit")
def submit_exam(
    sub_id: int, 
    req: SaveProgressRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    sub = db.query(Submission).filter(Submission.id == sub_id, Submission.user_id == current_user.id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # If already completed normally, return status
    if sub.is_completed and sub.status == "submitted":
        return {
            "message": "Quiz was already submitted.",
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None
        }

    # Update candidate's answers
    answers = sub.get_answers()
    answers.update(req.answers)
    sub.set_answers(answers)

    # Calculate Score
    quiz = sub.quiz
    total_points = 0.0
    earned_points = 0.0
    coding_results = {}

    for question in quiz.questions:
        total_points += (question.points or 5)
        user_ans = answers.get(str(question.id), "")

        if question.question_type == "mcq":
            user_choice = str(user_ans).strip().upper()
            if len(user_choice) > 1 and user_choice[1] == ')':
                user_choice = user_choice[0]
            corr = question.correct_answer.strip().upper()
            if user_choice and (user_choice == corr or user_choice.startswith(corr)):
                earned_points += (question.points or 5)

        elif question.question_type == "coding":
            all_cases = question.get_test_cases(include_hidden=True)
            if all_cases and str(user_ans).strip():
                exec_result = run_all_test_cases(str(user_ans), all_cases, run_hidden=True)
                coding_results[str(question.id)] = exec_result
                earned_points += (exec_result["score_ratio"] * (question.points or 10))
            else:
                coding_results[str(question.id)] = {"passed": 0, "total": len(all_cases), "all_passed": False}

        elif question.question_type == "short_answer":
            if str(user_ans).strip().lower() == question.correct_answer.strip().lower():
                earned_points += (question.points or 5)

    sub.score = earned_points
    sub.total_points = total_points
    sub.percentage = (earned_points / total_points * 100) if total_points > 0 else 0.0
    sub.submitted_at = datetime.utcnow()
    sub.is_completed = True

    max_allowed = quiz.max_violations if quiz else 3
    if sub.violation_count >= max_allowed:
        sub.status = "auto_submitted_violations"
    else:
        sub.status = "submitted"

    sub.set_coding_results(coding_results)
    db.commit()

    return {
        "message": "Quiz submitted successfully!",
        "confirmation": "Your responses have been securely recorded. In accordance with exam policies, results are confidential and visible to the administrator and course instructors only.",
        "submitted_at": sub.submitted_at.isoformat()
    }

# ----------------- RESULTS & ANALYTICS (ADMIN & INSTRUCTOR ONLY) -----------------
@app.get("/api/results")
def list_all_results(
    quiz_id: Optional[int] = None, 
    current_user: User = Depends(require_admin_or_instructor), 
    db: Session = Depends(get_db)
):
    """
    STRICT ACCESS: Admin & Instructor ONLY.
    Students will receive HTTP 403 Forbidden.
    """
    query = db.query(Submission).join(Quiz).filter(Submission.is_completed == True)

    if current_user.role == "instructor":
        query = query.filter(Quiz.instructor_id == current_user.id)
    if quiz_id:
        query = query.filter(Submission.quiz_id == quiz_id)

    submissions = query.order_by(Submission.submitted_at.desc()).all()
    return {
        "results": [s.to_dict(full_details=False) for s in submissions]
    }

@app.get("/api/results/{sub_id}")
def get_submission_detailed_report(
    sub_id: int, 
    current_user: User = Depends(require_admin_or_instructor), 
    db: Session = Depends(get_db)
):
    """
    STRICT ACCESS: Admin & Instructor ONLY.
    Returns complete breakdown, code submissions, test outputs, and proctoring audit log.
    """
    sub = db.query(Submission).filter(Submission.id == sub_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    if current_user.role == "instructor" and sub.quiz.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Build question-level breakdown
    breakdown = []
    answers = sub.get_answers()
    coding_res = sub.get_coding_results()

    for q in sub.quiz.questions:
        q_ans = answers.get(str(q.id), "")
        item = {
            "question_id": q.id,
            "title": q.title,
            "question_type": q.question_type,
            "points": q.points,
            "student_answer": q_ans,
            "correct_answer": q.correct_answer,
            "explanation": q.explanation,
        }
        if q.question_type == "coding":
            item["coding_result"] = coding_res.get(str(q.id), {})
            item["all_test_cases"] = q.get_test_cases(include_hidden=True)
        breakdown.append(item)

    data = sub.to_dict(full_details=True)
    data["questions_breakdown"] = breakdown
    return data

@app.get("/api/results/export/csv")
def export_results_csv(
    quiz_id: Optional[int] = None, 
    current_user: User = Depends(require_admin_or_instructor), 
    db: Session = Depends(get_db)
):
    """Generates downloadable CSV for instructor and admin."""
    query = db.query(Submission).join(Quiz).filter(Submission.is_completed == True)
    if current_user.role == "instructor":
        query = query.filter(Quiz.instructor_id == current_user.id)
    if quiz_id:
        query = query.filter(Submission.quiz_id == quiz_id)

    submissions = query.order_by(Submission.submitted_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Submission ID", "Quiz Code", "Quiz Title", "Candidate Name", "Candidate Email",
        "Score", "Total Points", "Percentage (%)", "Status", "Violations Count",
        "Started At", "Submitted At"
    ])

    for s in submissions:
        writer.writerow([
            s.id,
            s.quiz.code if s.quiz else "",
            s.quiz.title if s.quiz else "",
            s.user.full_name if s.user else "",
            s.user.email if s.user else "",
            round(s.score, 2),
            round(s.total_points, 2),
            round(s.percentage, 1),
            s.status,
            s.violation_count,
            s.started_at.strftime("%Y-%m-%d %H:%M:%S") if s.started_at else "",
            s.submitted_at.strftime("%Y-%m-%d %H:%M:%S") if s.submitted_at else ""
        ])

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=quiz_results_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

# ----------------- SERVE FRONTEND -----------------
FRONTEND_INDEX_PATH = os.path.join(os.path.dirname(__file__), "static", "index.html")

@app.get("/")
def serve_index():
    if os.path.exists(FRONTEND_INDEX_PATH):
        with open(FRONTEND_INDEX_PATH, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Proctored Quiz Platform Backend Running</h1>")

# Mount static folder
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
