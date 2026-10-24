import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables from .env if present
load_dotenv()

import tempfile

# Check for Supabase / PostgreSQL or fallback to local SQLite
raw_db_url = os.getenv("DATABASE_URL")

if raw_db_url and not raw_db_url.startswith("sqlite"):
    # Supabase / Heroku sometimes provide postgres:// which SQLAlchemy 2.0 requires as postgresql://
    if raw_db_url.startswith("postgres://"):
        DATABASE_URL = raw_db_url.replace("postgres://", "postgresql://", 1)
    else:
        DATABASE_URL = raw_db_url
    is_sqlite = False
else:
    is_sqlite = True
    # Serverless filesystem resilience:
    # In serverless platforms (Vercel, AWS Lambda, Netlify), current working directory is read-only.
    # We test if the local directory is writable; if not, safely place the SQLite file in tempfile.gettempdir().
    local_dir = os.path.dirname(os.path.abspath(__file__))
    if os.access(local_dir, os.W_OK):
        DB_PATH = os.path.join(local_dir, "quiz_system.db")
    else:
        DB_PATH = os.path.join(tempfile.gettempdir(), "quiz_system.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"

if is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30.0}
    )
    # Enable SQLite Write-Ahead Logging (WAL) mode for concurrency
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
        except Exception:
            pass
else:
    # Supabase PostgreSQL Configuration for Serverless & Long-running:
    # pool_pre_ping=True avoids disconnected socket errors across serverless invocations
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
