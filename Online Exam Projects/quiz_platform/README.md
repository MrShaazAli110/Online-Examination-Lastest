# 🛡️ ProctorCode: Multi-Tenant Quiz & Coding Assessment Platform

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Database](https://img.shields.io/badge/Database-SQLite%20(WAL)%20%7C%20Supabase%20PostgreSQL-336791?logo=postgresql)](https://supabase.com/)
[![TailwindCSS](https://img.shields.io/badge/Frontend-TailwindCSS%20CDN-38bdf8?logo=tailwindcss)](https://tailwindcss.com/)
[![Proctoring](https://img.shields.io/badge/Proctoring-Active%20Anti--Cheat%20HUD-red?logo=security)](https://github.com/)

**ProctorCode** is a high-concurrency, enterprise-grade assessment platform designed to host simultaneous multiple-choice quizzes and interactive programming challenges with strict anti-cheating proctoring, cursor movement tracking, automated document parsing (Word, PDF, TXT), and role-restricted results analytics.

---

## 📑 Table of Contents
1. [Key Features](#-key-features)
2. [Anti-Cheating & Movement Detection Architecture](#-anti-cheating--movement-detection-architecture)
3. [Dual-Format Assessments (Quiz + Coding)](#-dual-format-assessments-quiz--coding)
4. [Document Question Uploader (Word, PDF, TXT)](#-document-question-uploader-word-pdf-txt)
5. [Role-Based Access & Result Privacy](#-role-based-access--result-privacy)
6. [Supabase Setup & Upload Guide](#-supabase-setup--upload-guide)
7. [Serverless Deployment (Vercel & Netlify)](#-serverless-deployment-vercel--netlify)
8. [GitHub Upload Instructions](#-github-upload-instructions)
9. [Default Demo Accounts](#-default-demo-accounts)
10. [Quick Start & Local Setup](#-quick-start--local-setup)
11. [REST API Documentation](#-rest-api-documentation)
12. [Project Directory Structure](#-project-directory-structure)


---

## 🌟 Key Features

* **Simultaneous Multi-Tenancy**: Host dozens of independent exams simultaneously with unique join codes (e.g., `PYTHON-101`, `WEB-CS-202`). Concurrent candidates take tests without data collisions or database locks.
* **Dual-Format Questions**:
  * **MCQ**: Choices `A`, `B`, `C`, `D`, automated scoring, points allocation, and instructor explanations.
  * **In-Browser Code Execution**: Live Python 3 code runner with standard input (`stdin`) and output (`stdout`) validation, real-time sample test execution, and hidden evaluation test cases.
* **Strict Anti-Cheating & Movement Tracking**:
  * Tab-switch and window-blur detection (`Alt+Tab`, window minimize, or switching tabs).
  * Cursor departure tracking (detects when mouse leaves the exam viewport perimeter).
  * Mandatory full-screen enforcement with strike penalties on exit.
  * Keyboard shortcut and clipboard blocking (`F12`, `Ctrl+Shift+I`, `Ctrl+U`, copy/paste).
  * Automated disqualification when violation limits are exceeded.
* **Document Question Uploader**:
  * Parses Microsoft Word (`.docx`), PDF (`.pdf`), and plain text (`.txt`) documents into structured questions with answers.
  * Pre-import interactive preview modal.
* **Confidential Results (Admin & Instructor ONLY)**:
  * Students see only a secure submission confirmation.
  * Detailed grade book, code submissions, and a timestamped **Proctoring Violation Timeline** reserved exclusively for instructors and administrators.
  * One-click CSV spreadsheet export.
* **Hybrid Database**: Runs locally on SQLite with **Write-Ahead Logging (`WAL`)** or seamlessly connects to **Supabase PostgreSQL** in the cloud.

---

## 🔒 Anti-Cheating & Movement Detection Architecture

```
+--------------------------------------------------------------------------+
|                       STUDENT BROWSER EXAM VIEWPORT                     |
|                                                                          |
|  [Tab Switch / Visibility Change]  --> Event: document.visibilitychange  |
|  [Window Defocus / Alt+Tab]        --> Event: window.onblur              |
|  [Cursor Left Screen Boundary]     --> Event: document.mouseout/mouseleave|
|  [Exited Full-Screen Lockdown]     --> Event: document.fullscreenchange  |
|  [DevTools / Copy-Paste Attempt]   --> Event: keydown (F12, Ctrl+C/V)    |
+------------------------------------+-------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                       FRONTEND PROCTORING ENGINE                         |
|  1. Synthesizes audible alarm via Web Audio API.                         |
|  2. Displays Security Alert Modal with remaining chances.                |
|  3. Pulses the live Violation Counter HUD.                               |
|  4. Dispatches POST /api/submissions/{id}/record-violation.              |
+------------------------------------+-------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                        FASTAPI PROCTORING BACKEND                        |
|  1. Logs timestamped event to database audit table.                      |
|  2. Evaluates: (violation_count >= max_violations).                      |
|  3. If limit reached: Sets status="auto_submitted_violations", grades   |
|     current answers, and automatically terminates candidate session.     |
+--------------------------------------------------------------------------+
```

---

## 💻 Dual-Format Assessments (Quiz + Coding)

### Multiple Choice Questions (MCQ)
* Options selectable via radio buttons.
* Real-time auto-saving every 15 seconds.
* Randomized ordering capability and point weightings.

### Live Coding Arena
* Built-in code editor with syntax formatting and Tab key indentation.
* **"Run Sample Tests"**: Candidates can test custom input against sample test cases and inspect real-time `stdout`, execution runtime (in ms), and test status before submitting.
* **Sandboxed Execution**: Subprocess runner enforces a strict 3-second timeout per test case and filters dangerous system operations (`os.system`, `subprocess`, `shutil.rmtree`).

---

## 📄 Document Question Uploader (Word, PDF, TXT)

Instructors can upload question banks in `.docx`, `.pdf`, or `.txt` format:

```text
1. What is the time complexity of binary search?
A) O(n)
B) O(log n)
C) O(n log n)
D) O(1)
Answer: B
Explanation: Binary search halves the search space each step.

[CODING]
Title: Sum of Two Numbers
Description: Read two space-separated integers from stdin and output their sum.
Points: 10
Starter:
import sys
a, b = map(int, sys.stdin.read().split())
print(a + b)
Test: 10 25 -> 35
Test: -5 15 -> 10
```

* Sample files are provided in [`sample_files/`](sample_files/) (`sample_quiz.docx`, `sample_quiz.pdf`, `sample_quiz.txt`).

---

## ⚡ Supabase Setup & Upload Guide

ProctorCode is fully prepared for Supabase. You can host the PostgreSQL database and file storage directly on Supabase.

### Step 1: Create a Supabase Project
1. Go to [https://supabase.com](https://supabase.com) and sign in.
2. Click **New Project**, choose a name (e.g. `proctor-code`), and set a secure database password.

### Step 2: Run the SQL Schema Migration
1. In your Supabase dashboard, click the **SQL Editor** tab in the left sidebar.
2. Click **New Query**.
3. Open [`supabase_schema.sql`](supabase_schema.sql) from this project, copy all contents, paste it into the SQL Editor, and click **Run**.
4. This creates all tables (`users`, `quizzes`, `questions`, `submissions`), indexes, Row Level Security policies, and seeds initial accounts.

### Step 3: Connect Your Application to Supabase
1. In Supabase, navigate to **Project Settings** -> **Database**.
2. Under **Connection string**, select **URI**.
3. Copy the URI (e.g., `postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`).
4. Copy `.env.example` to `.env` in the project root:
   ```bash
   cp .env.example .env
   ```
5. Set `DATABASE_URL` in your `.env`:
   ```env
   DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   SUPABASE_URL=https://[YOUR-PROJECT-REF].supabase.co
   SUPABASE_KEY=[YOUR-SUPABASE-ANON-KEY]
   SUPABASE_BUCKET=quiz-documents
   ```

### Step 4: Create Supabase Storage Bucket (Optional for Documents)
1. In Supabase, click **Storage** in the left sidebar.
2. Click **New Bucket** and name it `quiz-documents`.
3. Set the bucket to **Public** so uploaded assessment files and exports can be viewed.

---

## ☁️ Serverless Deployment (Vercel & Netlify)

ProctorCode is pre-configured for 100% serverless deployment without losing any live coding or proctoring features.

### Option A: Deploy to Vercel (Recommended)
1. Push your latest code to your GitHub repository:
   ```bash
   git add .
   git commit -m "Configure serverless architecture"
   git push origin main
   ```
2. Go to [Vercel](https://vercel.com) and click **"Add New..."** -> **"Project"**.
3. Import your GitHub repository (`MrShaazAli110/Online-Examination-`).
4. In **Environment Variables**, add:
   - `DATABASE_URL`: `postgresql://postgres:[YOUR-PASSWORD]@db.uxfttpvqfntpzhcqxbwx.supabase.co:5432/postgres`
   - `SUPABASE_URL`: `https://uxfttpvqfntpzhcqxbwx.supabase.co`
   - `SUPABASE_KEY`: Your Supabase anon key
   - `SUPABASE_BUCKET`: `quiz-documents`
   - `SECRET_KEY`: `super-secret-secure-proctor-quiz-key-2026`
5. Click **Deploy**. Vercel will automatically build and host the app via `vercel.json` and `api/index.py`.

### Option B: Deploy to Netlify
1. Connect your repository on [Netlify](https://app.netlify.com/).
2. Under **Site Configuration** -> **Environment Variables**, add the same variables as above (`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_BUCKET`, `SECRET_KEY`).
3. Netlify will automatically detect `netlify.toml` and deploy the frontend and serverless functions via Mangum.

---

## 🐙 GitHub Upload Instructions

The repository has been initialized with clean Git history on the `main` branch.

### Step 1: Create a Remote Repository
1. Open [GitHub - New Repository](https://github.com/new).
2. Set the repository name (e.g. `proctor-code-platform`).
3. Leave **"Initialize with README"** unchecked.
4. Click **Create repository**.

### Step 2: Push to GitHub
Run the following commands in your terminal:

```powershell
cd "h:\Antigravity Projects\quiz_platform"
git remote add origin https://github.com/<YOUR-USERNAME>/<YOUR-REPO-NAME>.git
git branch -M main
git push -u origin main
```

---

## 🔑 Default Demo Accounts

| Role | Username | Password | Permissions |
|---|---|---|---|
| **Administrator** | `admin` | `admin123` | Full system control, all quizzes & results |
| **Instructor** | `instructor` | `prof123` | Create/edit quizzes, modify duration, view audit logs |
| **Candidate 1** | `student1` | `user123` | Take proctored exams under lockdown |
| **Candidate 2** | `student2` | `user123` | Take proctored exams under lockdown |

---

## 🚀 Quick Start & Local Setup

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/<YOUR-USERNAME>/<YOUR-REPO-NAME>.git
cd quiz_platform
python -m pip install -r requirements.txt
```

### 2. Start the Server
```bash
python run.py
```
Or with Uvicorn:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. Open Web Application
Navigate to **http://127.0.0.1:8000** in your browser.

### 4. Run Automated End-to-End Test Suite
```bash
python test_full_suite.py
```

---

## 📡 REST API Documentation

### Authentication
* `POST /api/auth/register` — Register student, instructor, or admin account.
* `POST /api/auth/login` — Sign in and obtain JWT bearer token.
* `GET /api/auth/me` — Return current authenticated user profile.

### Quiz & Question Management
* `GET /api/quizzes` — List quizzes (students receive active exams; staff receive full statistics).
* `GET /api/quizzes/{id}` — Get quiz details (students receive masked questions without answers; staff receive solutions).
* `POST /api/quizzes` — Create quiz (title, code, duration, max violations).
* `PUT /api/quizzes/{id}` — Update quiz duration, rules, or active status.
* `DELETE /api/quizzes/{id}` — Delete quiz.
* `POST /api/quizzes/{id}/questions` — Add MCQ or Coding challenge.
* `DELETE /api/quizzes/{id}/questions/{qid}` — Delete question.
* `POST /api/quizzes/parse-file-preview` — Parse `.docx`, `.pdf`, or `.txt` file for interactive preview.
* `POST /api/quizzes/{id}/upload-questions` — Parse and append questions directly to quiz.

### Code Runner & Exam Session
* `POST /api/code/run-sample` — Execute Python code against sample test cases in real-time.
* `POST /api/quizzes/{id}/start` — Start proctored exam session with timezone-safe countdown.
* `POST /api/submissions/{id}/record-violation` — Record proctoring infraction and auto-disqualify if limit reached.
* `POST /api/submissions/{id}/save-progress` — Periodic auto-save.
* `POST /api/submissions/{id}/submit` — Final exam submission and score calculation.

### Results & Proctoring Audit (Admin & Instructor ONLY)
* `GET /api/results` — List submissions (returns `403 Forbidden` for students).
* `GET /api/results/{id}` — Full candidate report with code submissions, test outputs, and timestamped proctoring violation timeline.
* `GET /api/results/export/csv` — Download complete grade book in CSV format.

---

## 📁 Project Directory Structure

```
quiz_platform/
├── app/
│   ├── main.py              # FastAPI application & API endpoints
│   ├── models.py            # SQLAlchemy models (User, Quiz, Question, Submission)
│   ├── database.py          # Database configuration (SQLite WAL & Supabase PostgreSQL)
│   ├── auth.py              # JWT tokens, PBKDF2 hashing, and role guards
│   ├── parsers.py           # Word (.docx), PDF (.pdf), and Text (.txt) parsers
│   ├── runner.py            # Sandboxed Python code execution engine
│   ├── supabase_client.py   # Supabase Storage & client helpers
│   ├── seed_data.py         # Initial seed quizzes, coding problems, and users
│   └── static/
│       ├── index.html       # Single-Page UI with Tailwind CSS & modals
│       └── app.js           # Client-side engine, timer, and proctoring event listeners
├── sample_files/            # Sample question documents for testing
│   ├── sample_quiz.docx     # Microsoft Word format sample
│   ├── sample_quiz.pdf      # PDF format sample
│   └── sample_quiz.txt      # Plain text format sample
├── supabase_schema.sql      # Supabase PostgreSQL DDL migration script
├── .env.example             # Configuration template for Supabase & server
├── .gitignore               # Git ignore rules for Python & database files
├── requirements.txt         # Python project dependencies
├── run.py                   # Application startup entry point
├── test_full_suite.py       # End-to-end verification test suite
└── README.md                # Comprehensive documentation
```
