import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "quiz-documents")

_supabase_client = None

def get_supabase():
    """Initializes and returns the Supabase client if credentials are configured."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    try:
        from supabase import create_client, Client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _supabase_client
    except Exception as e:
        print(f"Warning: Failed to initialize Supabase client: {e}")
        return None

def upload_to_supabase_storage(filename: str, file_bytes: bytes, content_type: str = "application/octet-stream") -> Optional[str]:
    """
    Uploads a question document or test report to Supabase Storage.
    Returns the public URL if successful, or None.
    """
    client = get_supabase()
    if not client:
        return None

    try:
        # Check / create bucket if needed
        # Upload file bytes to the bucket
        file_path = f"uploads/{filename}"
        res = client.storage.from_(SUPABASE_BUCKET).upload(
            file_path,
            file_bytes,
            file_options={"content-type": content_type, "upsert": "true"}
        )
        # Get public URL
        public_url = client.storage.from_(SUPABASE_BUCKET).get_public_url(file_path)
        return public_url
    except Exception as e:
        print(f"Supabase Storage upload warning: {e}")
        return None
