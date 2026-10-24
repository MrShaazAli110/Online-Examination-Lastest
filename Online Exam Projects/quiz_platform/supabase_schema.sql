-- =========================================================================
-- PROCTORCODE: SUPABASE POSTGRESQL DATABASE SCHEMA & MIGRATION SCRIPT
-- =========================================================================
-- Run this script directly in your Supabase Dashboard:
-- 1. Log in to https://supabase.com
-- 2. Open your project -> Click "SQL Editor" in the left sidebar
-- 3. Click "New query" -> Paste this entire script -> Click "Run"
-- =========================================================================

-- Enable pgcrypto for UUID and hash generation if needed
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS public.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) DEFAULT 'student' NOT NULL CHECK (role IN ('admin', 'instructor', 'student')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Index on username and email
CREATE INDEX IF NOT EXISTS idx_users_username ON public.users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);

-- 2. QUIZZES TABLE
CREATE TABLE IF NOT EXISTS public.quizzes (
    id SERIAL PRIMARY KEY,
    title VARCHAR(150) NOT NULL,
    description TEXT DEFAULT '',
    code VARCHAR(30) UNIQUE NOT NULL,
    instructor_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    duration_minutes INTEGER DEFAULT 30 NOT NULL,
    max_violations INTEGER DEFAULT 3 NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_quizzes_code ON public.quizzes(code);
CREATE INDEX IF NOT EXISTS idx_quizzes_instructor ON public.quizzes(instructor_id);
CREATE INDEX IF NOT EXISTS idx_quizzes_active ON public.quizzes(is_active);

-- 3. QUESTIONS TABLE
CREATE TABLE IF NOT EXISTS public.questions (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER NOT NULL REFERENCES public.quizzes(id) ON DELETE CASCADE,
    question_type VARCHAR(20) DEFAULT 'mcq' NOT NULL CHECK (question_type IN ('mcq', 'coding', 'short_answer')),
    title VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    options_json TEXT DEFAULT '[]',
    correct_answer TEXT DEFAULT '',
    explanation TEXT DEFAULT '',
    points INTEGER DEFAULT 5 NOT NULL,
    order_idx INTEGER DEFAULT 0 NOT NULL,
    starter_code TEXT DEFAULT '',
    language VARCHAR(30) DEFAULT 'python',
    test_cases_json TEXT DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_questions_quiz ON public.questions(quiz_id);
CREATE INDEX IF NOT EXISTS idx_questions_order ON public.questions(quiz_id, order_idx);

-- 4. SUBMISSIONS & PROCTORING AUDIT LOGS TABLE
CREATE TABLE IF NOT EXISTS public.submissions (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER NOT NULL REFERENCES public.quizzes(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE,
    is_completed BOOLEAN DEFAULT FALSE NOT NULL,
    score DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    total_points DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    percentage DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
    status VARCHAR(30) DEFAULT 'in_progress' NOT NULL,
    answers_json TEXT DEFAULT '{}',
    coding_results_json TEXT DEFAULT '{}',
    violation_count INTEGER DEFAULT 0 NOT NULL,
    violation_logs_json TEXT DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_submissions_quiz_user ON public.submissions(quiz_id, user_id);
CREATE INDEX IF NOT EXISTS idx_submissions_completed ON public.submissions(is_completed);

-- =========================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =========================================================================
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quizzes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY;

-- Allow read access to all registered entities via API backend
CREATE POLICY "Allow backend service access" ON public.users FOR ALL USING (true);
CREATE POLICY "Allow backend service quizzes" ON public.quizzes FOR ALL USING (true);
CREATE POLICY "Allow backend service questions" ON public.questions FOR ALL USING (true);
CREATE POLICY "Allow backend service submissions" ON public.submissions FOR ALL USING (true);

-- =========================================================================
-- INITIAL SEED USERS FOR SUPABASE (NO DEMO QUIZZES)
-- =========================================================================
-- Seed Passwords:
-- admin: admin123 -> a435e7d17478d1ad6ea9136ca02410a74797010f3c5b597cbe6ea1fe9c43d26d
-- instructor: prof123 -> b7329b34005b4b7dd1517409c9162955f2d655fba7192f441ba59560f78d9136

INSERT INTO public.users (id, username, email, password_hash, full_name, role)
VALUES 
    (1, 'admin', 'admin@platform.com', 'a435e7d17478d1ad6ea9136ca02410a74797010f3c5b597cbe6ea1fe9c43d26d', 'System Administrator', 'admin'),
    (2, 'instructor', 'instructor@university.edu', 'b7329b34005b4b7dd1517409c9162955f2d655fba7192f441ba59560f78d9136', 'Course Instructor', 'instructor')
ON CONFLICT (username) DO NOTHING;

-- Reset sequence for users
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));

