import json
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from .models import User, Quiz, Question, Submission
from .supabase_client import get_supabase

logger = logging.getLogger("proctorcode.supabase_sync")

def sync_from_supabase(db: Session):
    """
    Syncs quizzes, questions, and users from Supabase into the local database.
    Ensures that when running in serverless or local mode, data is never lost
    and never falls back to demo data.
    """
    sb = get_supabase()
    if not sb:
        return

    try:
        # 1. Sync Users from Supabase
        user_res = sb.table("users").select("*").execute()
        if user_res and user_res.data:
            for u_data in user_res.data:
                existing_user = db.query(User).filter(
                    (User.id == u_data["id"]) | (User.username == u_data["username"])
                ).first()
                if not existing_user:
                    new_u = User(
                        id=u_data["id"],
                        username=u_data["username"],
                        email=u_data.get("email", f"{u_data['username']}@platform.com"),
                        password_hash=u_data.get("password_hash", ""),
                        full_name=u_data.get("full_name", u_data["username"]),
                        role=u_data.get("role", "student")
                    )
                    db.add(new_u)
            db.commit()

        # 2. Sync Quizzes from Supabase
        quiz_res = sb.table("quizzes").select("*").execute()
        sb_quizzes = quiz_res.data if quiz_res and quiz_res.data else []
        sb_quiz_ids = {q["id"] for q in sb_quizzes}

        for q_data in sb_quizzes:
            local_quiz = db.query(Quiz).filter(Quiz.id == q_data["id"]).first()
            if not local_quiz:
                # Also check by code in case id sequence differed
                local_quiz = db.query(Quiz).filter(Quiz.code == q_data["code"]).first()

            # Ensure instructor exists locally
            inst_id = q_data.get("instructor_id") or 1
            inst = db.query(User).filter(User.id == inst_id).first()
            if not inst:
                first_admin = db.query(User).filter(User.role == "admin").first()
                inst_id = first_admin.id if first_admin else 1

            if not local_quiz:
                local_quiz = Quiz(
                    id=q_data["id"],
                    title=q_data["title"],
                    description=q_data.get("description", ""),
                    code=q_data["code"],
                    instructor_id=inst_id,
                    duration_minutes=q_data.get("duration_minutes", 30),
                    max_violations=q_data.get("max_violations", 3),
                    is_active=q_data.get("is_active", True)
                )
                db.add(local_quiz)
            else:
                local_quiz.title = q_data["title"]
                local_quiz.description = q_data.get("description", "")
                local_quiz.code = q_data["code"]
                local_quiz.duration_minutes = q_data.get("duration_minutes", 30)
                local_quiz.max_violations = q_data.get("max_violations", 3)
                local_quiz.is_active = q_data.get("is_active", True)

        db.commit()

        # 3. Sync Questions from Supabase
        q_res = sb.table("questions").select("*").execute()
        if q_res and q_res.data:
            for qn in q_res.data:
                local_qn = db.query(Question).filter(Question.id == qn["id"]).first()
                if not local_qn:
                    local_qn = Question(
                        id=qn["id"],
                        quiz_id=qn["quiz_id"],
                        question_type=qn.get("question_type", "mcq"),
                        title=qn.get("title", ""),
                        description=qn.get("description", ""),
                        options_json=qn.get("options_json", "[]"),
                        correct_answer=qn.get("correct_answer", ""),
                        explanation=qn.get("explanation", ""),
                        points=qn.get("points", 5),
                        order_idx=qn.get("order_idx", 0),
                        starter_code=qn.get("starter_code", ""),
                        language=qn.get("language", "python"),
                        test_cases_json=qn.get("test_cases_json", "[]")
                    )
                    db.add(local_qn)
                else:
                    local_qn.title = qn.get("title", "")
                    local_qn.description = qn.get("description", "")
                    local_qn.options_json = qn.get("options_json", "[]")
                    local_qn.correct_answer = qn.get("correct_answer", "")
                    local_qn.explanation = qn.get("explanation", "")
                    local_qn.points = qn.get("points", 5)
                    local_qn.order_idx = qn.get("order_idx", 0)
                    local_qn.starter_code = qn.get("starter_code", "")
                    local_qn.language = qn.get("language", "python")
                    local_qn.test_cases_json = qn.get("test_cases_json", "[]")
            db.commit()

        logger.info(f"Supabase sync complete: {len(sb_quizzes)} quizzes in sync.")
    except Exception as e:
        logger.warning(f"Supabase sync notice: {e}")

def sync_quiz_to_supabase(quiz: Quiz):
    """Upserts a single quiz to Supabase."""
    sb = get_supabase()
    if not sb:
        return
    try:
        data = {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description or "",
            "code": quiz.code,
            "instructor_id": quiz.instructor_id,
            "duration_minutes": quiz.duration_minutes,
            "max_violations": quiz.max_violations,
            "is_active": quiz.is_active
        }
        sb.table("quizzes").upsert(data).execute()
    except Exception as e:
        logger.warning(f"Failed to sync quiz {quiz.id} to Supabase: {e}")

def delete_quiz_from_supabase(quiz_id: int):
    """Deletes a quiz and all cascading questions/submissions from Supabase."""
    sb = get_supabase()
    if not sb:
        return
    try:
        # Explicitly delete children first to be safe
        sb.table("submissions").delete().eq("quiz_id", quiz_id).execute()
        sb.table("questions").delete().eq("quiz_id", quiz_id).execute()
        sb.table("quizzes").delete().eq("id", quiz_id).execute()
    except Exception as e:
        logger.warning(f"Failed to delete quiz {quiz_id} from Supabase: {e}")

def sync_question_to_supabase(question: Question):
    """Upserts a question to Supabase."""
    sb = get_supabase()
    if not sb:
        return
    try:
        data = {
            "id": question.id,
            "quiz_id": question.quiz_id,
            "question_type": question.question_type,
            "title": question.title,
            "description": question.description or "",
            "options_json": question.options_json or "[]",
            "correct_answer": question.correct_answer or "",
            "explanation": question.explanation or "",
            "points": question.points,
            "order_idx": question.order_idx,
            "starter_code": question.starter_code or "",
            "language": question.language or "python",
            "test_cases_json": question.test_cases_json or "[]"
        }
        sb.table("questions").upsert(data).execute()
    except Exception as e:
        logger.warning(f"Failed to sync question {question.id} to Supabase: {e}")

def delete_question_from_supabase(question_id: int):
    """Deletes a question from Supabase."""
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("questions").delete().eq("id", question_id).execute()
    except Exception as e:
        logger.warning(f"Failed to delete question {question_id} from Supabase: {e}")

def sync_user_to_supabase(user: User):
    """Upserts a user to Supabase."""
    sb = get_supabase()
    if not sb:
        return
    try:
        data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "password_hash": user.password_hash,
            "full_name": user.full_name,
            "role": user.role
        }
        sb.table("users").upsert(data).execute()
    except Exception as e:
        logger.warning(f"Failed to sync user {user.username} to Supabase: {e}")
