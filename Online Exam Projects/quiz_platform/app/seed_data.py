from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import User, Quiz, Question, Submission
from .auth import hash_password
from .supabase_sync import sync_from_supabase, sync_user_to_supabase

def seed_database():
    """
    Initializes required database schema and default administrative accounts.
    Demo quizzes, demo questions, and dummy student submissions have been completely removed.
    Data is synced directly with Supabase without fallback to demo data.
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Ensure default Admin account exists
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@platform.com",
                password_hash=hash_password("admin123"),
                full_name="System Administrator",
                role="admin"
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            sync_user_to_supabase(admin)

        # 2. Ensure default Instructor account exists
        instructor = db.query(User).filter(User.username == "instructor").first()
        if not instructor:
            instructor = User(
                username="instructor",
                email="instructor@university.edu",
                password_hash=hash_password("prof123"),
                full_name="Course Instructor",
                role="instructor"
            )
            db.add(instructor)
            db.commit()
            db.refresh(instructor)
            sync_user_to_supabase(instructor)

        # 3. Synchronize any persistent quizzes and questions from Supabase
        sync_from_supabase(db)

    except Exception as e:
        print(f"Database initialization notice: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
