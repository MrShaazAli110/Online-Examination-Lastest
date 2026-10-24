"""
Automatic Schema Pusher for Supabase PostgreSQL
Usage:
    python push_schema.py
"""
import os
import sys
import getpass
from dotenv import load_dotenv

load_dotenv()

def push_schema():
    print("=" * 60)
    print("  PROCTORCODE: Automatic Supabase Schema Pusher")
    print("=" * 60)

    db_url = os.getenv("DATABASE_URL")
    project_ref = "uxfttpvqfntpzhcqxbwx"

    # If DATABASE_URL is not set or placeholder
    if not db_url or "[YOUR-PASSWORD]" in db_url or "[PROJECT-REF]" in db_url:
        print(f"\nTarget Supabase Project Ref: {project_ref}")
        password = getpass.getpass("Enter your Supabase database password: ").strip()
        if not password:
            print("Error: Password cannot be empty.")
            sys.exit(1)
        db_url = f"postgresql://postgres:{password}@db.{project_ref}.supabase.co:5432/postgres"

    schema_file = os.path.join(os.path.dirname(__file__), "supabase_schema.sql")
    if not os.path.exists(schema_file):
        print(f"Error: Schema file '{schema_file}' not found.")
        sys.exit(1)

    with open(schema_file, "r", encoding="utf-8") as f:
        sql = f.read()

    print("\nConnecting to Supabase PostgreSQL database...")
    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            print("Executing schema migration and seed script...")
            cur.execute(sql)
        conn.close()
        print("\nSUCCESS: All tables, indexes, RLS policies, and seed users pushed to Supabase successfully!")
    except ImportError:
        print("\n'psycopg2' is not installed. Installing psycopg2-binary or run:")
        print("  pip install psycopg2-binary")
        sys.exit(1)
    except Exception as e:
        print(f"\nExecution failed: {e}")
        print("\nHint: Check your database password or project connection settings.")
        sys.exit(1)

if __name__ == "__main__":
    push_schema()
