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

-- ROW LEVEL SECURITY (RLS) POLICIES
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quizzes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.submissions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow backend service access" ON public.users FOR ALL USING (true);
CREATE POLICY "Allow backend service quizzes" ON public.quizzes FOR ALL USING (true);
CREATE POLICY "Allow backend service questions" ON public.questions FOR ALL USING (true);
CREATE POLICY "Allow backend service submissions" ON public.submissions FOR ALL USING (true);

-- INITIAL SEED DATA
INSERT INTO public.users (id, username, email, password_hash, full_name, role)
VALUES 
    (1, 'admin', 'admin@platform.com', 'a435e7d17478d1ad6ea9136ca02410a74797010f3c5b597cbe6ea1fe9c43d26d', 'System Administrator', 'admin'),
    (2, 'instructor', 'instructor@university.edu', 'b7329b34005b4b7dd1517409c9162955f2d655fba7192f441ba59560f78d9136', 'Prof. Alex Reynolds', 'instructor'),
    (3, 'student1', 'emma@student.edu', 'c95dfbc16d7aeb9e4f2e5a6efc4faee4580bf13e2bbdc1f4b025178619bcad1b', 'Emma Watson', 'student'),
    (4, 'student2', 'david@student.edu', 'c95dfbc16d7aeb9e4f2e5a6efc4faee4580bf13e2bbdc1f4b025178619bcad1b', 'David Miller', 'student')
ON CONFLICT (username) DO NOTHING;

SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));

INSERT INTO public.quizzes (id, title, description, code, instructor_id, duration_minutes, max_violations, is_active)
VALUES
    (1, 'Python Core & Algorithms Assessment', 'Comprehensive technical exam covering Python memory model, algorithmic complexity, and live coding challenges with proctored tab-switch monitoring.', 'PYTHON-101', 2, 25, 3, true),
    (2, 'Web Architecture & Data Structures Challenge', 'Test your understanding of HTTP protocols, database indexing, caching strategies, and data structures.', 'WEB-CS-202', 2, 30, 3, true)
ON CONFLICT (code) DO NOTHING;

SELECT setval('quizzes_id_seq', (SELECT MAX(id) FROM quizzes));

INSERT INTO public.questions (quiz_id, question_type, title, description, options_json, correct_answer, explanation, points, order_idx, starter_code, language, test_cases_json)
VALUES
    (1, 'mcq', 'What is the time complexity of lookup in a Python dictionary on average?', 'Consider standard hash table implementation with CPython.', '["A) O(1)", "B) O(log n)", "C) O(n)", "D) O(n log n)"]', 'A', 'Python dictionaries are implemented as hash tables with open addressing, yielding O(1) average lookup time.', 5, 1, '', 'python', '[]'),
    (1, 'mcq', 'Which of the following creates a deep copy in Python?', 'Choose the standard library mechanism.', '["A) list.copy()", "B) dict.copy()", "C) copy.deepcopy()", "D) slice operator [:]"]', 'C', 'copy.deepcopy() recursively copies all nested composite objects.', 5, 2, '', 'python', '[]'),
    (1, 'coding', 'Palindrome Number Checker', 'Write a python program that reads an integer n from standard input and prints True if it is a palindrome, otherwise False.', '[]', '', '', 15, 3, 'import sys\n\ndef is_palindrome(s: str) -> bool:\n    return s == s[::-1]\n\nif __name__ == ''__main__'':\n    inp = sys.stdin.read().strip()\n    if inp:\n        print(is_palindrome(inp))\n', 'python', '[{"input": "121", "expected_output": "True", "is_hidden": false}, {"input": "-121", "expected_output": "False", "is_hidden": false}, {"input": "10", "expected_output": "False", "is_hidden": true}, {"input": "12321", "expected_output": "True", "is_hidden": true}]'),
    (1, 'coding', 'Array Element Multiplier', 'Read an integer multiplier on line 1, and space-separated integers on line 2. Print the multiplied numbers separated by spaces.', '[]', '', '', 15, 4, 'import sys\n\nlines = sys.stdin.read().strip().split(''\n'')\nif len(lines) >= 2:\n    m = int(lines[0].strip())\n    nums = [int(x) * m for x in lines[1].split()]\n    print('' ''.join(map(str, nums)))\n', 'python', '[{"input": "2\n1 2 3 4", "expected_output": "2 4 6 8", "is_hidden": false}, {"input": "3\n5 10 15", "expected_output": "15 30 45", "is_hidden": false}, {"input": "0\n10 20 30", "expected_output": "0 0 0", "is_hidden": true}]');

INSERT INTO public.questions (quiz_id, question_type, title, description, options_json, correct_answer, explanation, points, order_idx, starter_code, language, test_cases_json)
VALUES
    (2, 'mcq', 'What HTTP status code is returned for an unauthorized authentication error?', '', '["A) 400 Bad Request", "B) 401 Unauthorized", "C) 403 Forbidden", "D) 404 Not Found"]', 'B', '401 Unauthorized indicates that the request lacks valid authentication credentials.', 5, 1, '', 'python', '[]'),
    (2, 'mcq', 'Which data structure operates on a First-In-First-Out (FIFO) basis?', '', '["A) Stack", "B) Queue", "C) Heap", "D) Binary Search Tree"]', 'B', 'A Queue operates in FIFO order.', 5, 2, '', 'python', '[]'),
    (2, 'coding', 'Even Numbers Filter', 'Read space-separated integers from stdin and output only the even numbers, separated by spaces. If none, output empty line.', '[]', '', '', 10, 3, 'import sys\n\ns = sys.stdin.read().strip()\nif s:\n    evens = [x for x in s.split() if int(x) % 2 == 0]\n    print('' ''.join(evens))\n', 'python', '[{"input": "1 2 3 4 5 6", "expected_output": "2 4 6", "is_hidden": false}, {"input": "11 13 15", "expected_output": "", "is_hidden": false}, {"input": "100 201 302", "expected_output": "100 302", "is_hidden": true}]');
