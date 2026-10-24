import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), default="student", nullable=False)  # admin, instructor, student
    created_at = Column(DateTime, default=datetime.utcnow)

    quizzes = relationship("Quiz", back_populates="instructor", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, default="")
    code = Column(String(30), unique=True, index=True, nullable=False)
    instructor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    duration_minutes = Column(Integer, default=30)
    max_violations = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    instructor = relationship("User", back_populates="quizzes")
    questions = relationship("Question", back_populates="quiz", cascade="all, delete-orphan", order_by="Question.order_idx")
    submissions = relationship("Submission", back_populates="quiz", cascade="all, delete-orphan")

    def to_dict(self, include_questions=False, is_admin_or_instructor=False):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "code": self.code,
            "instructor_id": self.instructor_id,
            "instructor_name": self.instructor.full_name if self.instructor else "Unknown",
            "duration_minutes": self.duration_minutes,
            "max_violations": self.max_violations,
            "is_active": self.is_active,
            "question_count": len(self.questions) if self.questions else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
        if include_questions:
            data["questions"] = [
                q.to_dict(include_solution=is_admin_or_instructor) 
                for q in self.questions
            ]
        return data

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    question_type = Column(String(20), default="mcq")  # mcq, coding, short_answer
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    options_json = Column(Text, default="[]")  # List of choices for MCQ
    correct_answer = Column(Text, default="")  # e.g. "B" or correct text
    explanation = Column(Text, default="")
    points = Column(Integer, default=5)
    order_idx = Column(Integer, default=0)

    # Programming specific fields
    starter_code = Column(Text, default="")
    language = Column(String(30), default="python")
    test_cases_json = Column(Text, default="[]")  # [{"input": "...", "expected_output": "...", "is_hidden": bool}]

    quiz = relationship("Quiz", back_populates="questions")

    def get_options(self):
        try:
            return json.loads(self.options_json or "[]")
        except:
            return []

    def set_options(self, opts):
        self.options_json = json.dumps(opts)

    def get_test_cases(self, include_hidden=False):
        try:
            cases = json.loads(self.test_cases_json or "[]")
            if not include_hidden:
                return [c for c in cases if not c.get("is_hidden", False)]
            return cases
        except:
            return []

    def set_test_cases(self, cases):
        self.test_cases_json = json.dumps(cases)

    def to_dict(self, include_solution=False):
        data = {
            "id": self.id,
            "quiz_id": self.quiz_id,
            "question_type": self.question_type,
            "title": self.title,
            "description": self.description,
            "options": self.get_options(),
            "points": self.points,
            "order_idx": self.order_idx,
            "language": self.language,
            "starter_code": self.starter_code,
            # Only reveal sample/public test cases to student; admin gets all
            "test_cases": self.get_test_cases(include_hidden=include_solution)
        }
        if include_solution:
            data["correct_answer"] = self.correct_answer
            data["explanation"] = self.explanation
            data["all_test_cases"] = self.get_test_cases(include_hidden=True)
        return data

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)
    score = Column(Float, default=0.0)
    total_points = Column(Float, default=0.0)
    percentage = Column(Float, default=0.0)
    status = Column(String(30), default="in_progress")  # in_progress, submitted, auto_submitted_violations, timed_out
    
    answers_json = Column(Text, default="{}")  # { question_id: answer/code }
    coding_results_json = Column(Text, default="{}")  # { question_id: execution test case results }
    violation_count = Column(Integer, default=0)
    violation_logs_json = Column(Text, default="[]")  # [{ timestamp, type, details }]

    quiz = relationship("Quiz", back_populates="submissions")
    user = relationship("User", back_populates="submissions")

    def get_answers(self):
        try:
            return json.loads(self.answers_json or "{}")
        except:
            return {}

    def set_answers(self, answers):
        self.answers_json = json.dumps(answers)

    def get_coding_results(self):
        try:
            return json.loads(self.coding_results_json or "{}")
        except:
            return {}

    def set_coding_results(self, res):
        self.coding_results_json = json.dumps(res)

    def get_violation_logs(self):
        try:
            return json.loads(self.violation_logs_json or "[]")
        except:
            return []

    def add_violation(self, v_type, details=""):
        logs = self.get_violation_logs()
        logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "type": v_type,
            "details": details
        })
        self.violation_logs_json = json.dumps(logs)
        self.violation_count = len(logs)

    def to_dict(self, full_details=False):
        data = {
            "id": self.id,
            "quiz_id": self.quiz_id,
            "quiz_title": self.quiz.title if self.quiz else "",
            "quiz_code": self.quiz.code if self.quiz else "",
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else "",
            "user_email": self.user.email if self.user else "",
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "is_completed": self.is_completed,
            "score": round(self.score, 2),
            "total_points": round(self.total_points, 2),
            "percentage": round(self.percentage, 1),
            "status": self.status,
            "violation_count": self.violation_count,
        }
        if full_details:
            data["answers"] = self.get_answers()
            data["coding_results"] = self.get_coding_results()
            data["violation_logs"] = self.get_violation_logs()
        return data
