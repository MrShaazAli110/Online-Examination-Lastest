import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User, Quiz, Question, Submission
from app.seed_data import seed_database

client = TestClient(app)

def test_full_platform():
    print("\n--- Running End-to-End ProctorCode Platform Verification ---")
    
    # 1. Test Login with Seed Admin
    print("\n[1] Testing Admin Login...")
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200, f"Admin login failed: {res.text}"
    admin_token = res.json()["access_token"]
    print("  [OK] Admin logged in successfully with JWT token")

    # 2. Test Login with Seed Instructor
    print("\n[2] Testing Instructor Login...")
    res = client.post("/api/auth/login", json={"username": "instructor", "password": "prof123"})
    assert res.status_code == 200, f"Instructor login failed: {res.text}"
    inst_token = res.json()["access_token"]
    print("  [OK] Instructor logged in successfully")

    # 3. Test Student Registration & Login
    print("\n[3] Testing Student Registration...")
    student_payload = {
        "username": "candidate_test",
        "email": "candidate_test@example.com",
        "password": "pass12345",
        "full_name": "Test Candidate",
        "role": "student"
    }
    res = client.post("/api/auth/register", json=student_payload)
    if res.status_code == 400: # Already exists in DB
        res = client.post("/api/auth/login", json={"username": "candidate_test", "password": "pass12345"})
    assert res.status_code == 200, f"Student auth failed: {res.text}"
    student_token = res.json()["access_token"]
    student_user = res.json()["user"]
    print(f"  [OK] Candidate registered & authenticated (User ID: {student_user['id']})")

    # 4. Test Instructor Quiz Creation & Duration Modification
    print("\n[4] Testing Quiz Creation and Duration Modification by Instructor...")
    quiz_payload = {
        "title": "Data Structures & Python Live Test",
        "description": "Multi-tenant exam with code execution and strict tab proctoring.",
        "code": "DS-PY-404",
        "duration_minutes": 45,
        "max_violations": 3
    }
    inst_headers = {"Authorization": f"Bearer {inst_token}"}
    res = client.post("/api/quizzes", json=quiz_payload, headers=inst_headers)
    if res.status_code == 400 and "already in use" in res.text:
        res = client.get("/api/quizzes", headers=inst_headers)
        quizzes = res.json()["quizzes"]
        new_quiz = next(q for q in quizzes if q["code"] == "DS-PY-404")
    else:
        assert res.status_code == 200, f"Create quiz failed: {res.text}"
        new_quiz = res.json()
    quiz_id = new_quiz["id"]
    print(f"  [OK] Created Quiz '{new_quiz['title']}' (ID: {quiz_id}, Code: {new_quiz['code']})")

    # Modify Quiz Duration (e.g. from 45 to 60 mins)
    res = client.put(f"/api/quizzes/{quiz_id}", json={"duration_minutes": 60, "max_violations": 4}, headers=inst_headers)
    assert res.status_code == 200, f"Modify quiz duration failed: {res.text}"
    updated_quiz = res.json()
    assert updated_quiz["duration_minutes"] == 60, "Duration was not updated"
    assert updated_quiz["max_violations"] == 4, "Max violations not updated"
    print(f"  [OK] Successfully modified Quiz Duration to {updated_quiz['duration_minutes']} mins, Violations to {updated_quiz['max_violations']}")

    # 5. Test File Uploads (.txt, .docx, .pdf)
    sample_dir = os.path.join(os.path.dirname(__file__), "sample_files")
    
    # 5a. Upload Text (.txt)
    txt_file = os.path.join(sample_dir, "sample_quiz.txt")
    if os.path.exists(txt_file):
        print("\n[5a] Testing Text File (.txt) Question Upload...")
        with open(txt_file, "rb") as f:
            res = client.post(f"/api/quizzes/{quiz_id}/upload-questions", files={"file": ("sample_quiz.txt", f, "text/plain")}, headers=inst_headers)
        assert res.status_code == 200, f"TXT upload failed: {res.text}"
        print(f"  [OK] Uploaded questions from TXT: {res.json()['message']}")

    # 5b. Upload Word (.docx)
    docx_file = os.path.join(sample_dir, "sample_quiz.docx")
    if os.path.exists(docx_file):
        print("\n[5b] Testing Word Document (.docx) Question Upload...")
        with open(docx_file, "rb") as f:
            res = client.post(f"/api/quizzes/{quiz_id}/upload-questions", files={"file": ("sample_quiz.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}, headers=inst_headers)
        assert res.status_code == 200, f"DOCX upload failed: {res.text}"
        print(f"  [OK] Uploaded questions from Word DOCX: {res.json()['message']}")

    # 5c. Upload PDF (.pdf)
    pdf_file = os.path.join(sample_dir, "sample_quiz.pdf")
    if os.path.exists(pdf_file):
        print("\n[5c] Testing PDF Document (.pdf) Question Upload...")
        with open(pdf_file, "rb") as f:
            res = client.post(f"/api/quizzes/{quiz_id}/upload-questions", files={"file": ("sample_quiz.pdf", f, "application/pdf")}, headers=inst_headers)
        assert res.status_code == 200, f"PDF upload failed: {res.text}"
        print(f"  [OK] Uploaded questions from PDF: {res.json()['message']}")

    # 6. Test Code Execution Engine (Runner)
    print("\n[6] Testing Live Code Execution Runner...")
    sample_code = """
import sys
line = sys.stdin.read().strip()
if line:
    print(int(line) ** 2)
"""
    test_cases = [
        {"input": "5", "expected_output": "25", "is_hidden": False},
        {"input": "12", "expected_output": "144", "is_hidden": False}
    ]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    res = client.post("/api/code/run-sample", json={"code": sample_code, "test_cases": test_cases}, headers=student_headers)
    assert res.status_code == 200, f"Code runner failed: {res.text}"
    run_res = res.json()
    assert run_res["all_passed"] is True, f"Code cases did not pass: {run_res}"
    print(f"  [OK] Code runner executed successfully! All {run_res['passed']}/{run_res['total']} sample test cases passed.")

    # 7. Test Student Exam Flow & Anti-Cheating Proctoring
    print("\n[7] Testing Student Starting Proctored Exam...")
    res = client.post(f"/api/quizzes/{quiz_id}/start", headers=student_headers)
    assert res.status_code == 200, f"Start exam failed: {res.text}"
    exam_session = res.json()
    sub_id = exam_session["submission_id"]
    quiz_meta = exam_session["quiz"]
    print(f"  [OK] Exam session initialized (Submission ID: {sub_id}, Questions: {len(quiz_meta['questions'])})")

    # Verify student does NOT receive correct_answer in question dict
    for q in quiz_meta["questions"]:
        assert "correct_answer" not in q, "Security leak: correct_answer exposed to candidate!"
        assert "all_test_cases" not in q, "Security leak: hidden test cases exposed to candidate!"
    print("  [OK] Verified questions are securely masked (no correct answers exposed to candidate)")

    # 8. Test Tab-Switch & Movement Violation Reporting
    print("\n[8] Testing Tab Switch & Movement Proctoring Detection...")
    v1 = client.post(f"/api/submissions/{sub_id}/record-violation", json={"violation_type": "tab_switch", "details": "Candidate switched to an external tab."}, headers=student_headers)
    assert v1.status_code == 200 and v1.json()["violation_count"] == 1
    print(f"  [OK] Violation 1 recorded: {v1.json()['message']}")

    v2 = client.post(f"/api/submissions/{sub_id}/record-violation", json={"violation_type": "mouse_left_window", "details": "Cursor departed proctored viewport boundary."}, headers=student_headers)
    assert v2.status_code == 200 and v2.json()["violation_count"] == 2
    print(f"  [OK] Violation 2 recorded: {v2.json()['message']}")

    # 9. Test Submitting Exam
    print("\n[9] Testing Candidate Submitting Exam...")
    answers = {}
    for q in quiz_meta["questions"]:
        if q["question_type"] == "mcq":
            answers[str(q["id"])] = "B"
        elif q["question_type"] == "coding":
            answers[str(q["id"])] = "import sys\\nprint('hello')\\n"

    res = client.post(f"/api/submissions/{sub_id}/submit", json={"answers": answers}, headers=student_headers)
    assert res.status_code == 200, f"Submit exam failed: {res.text}"
    submit_res = res.json()
    assert "score" not in submit_res, "Security breach: Score revealed to student upon submission!"
    print(f"  [OK] Quiz submitted successfully. Confirmation returned to student without disclosing grade.")

    # 10. Test Strict Access Control for Results
    print("\n[10] Verifying Results Access Security...")
    # Student MUST be blocked from viewing results
    res = client.get("/api/results", headers=student_headers)
    assert res.status_code == 403, f"Expected 403 Forbidden for student, got {res.status_code}"
    print("  [OK] Confirmed: Candidate receives 403 Forbidden when trying to access /api/results")

    # Admin and Instructor MUST be able to view results
    res = client.get("/api/results", headers=inst_headers)
    assert res.status_code == 200, f"Instructor results failed: {res.text}"
    results_list = res.json()["results"]
    assert len(results_list) > 0, "No results returned for instructor"
    print(f"  [OK] Confirmed: Instructor can view all {len(results_list)} submission results")

    # Detailed Audit Report with Proctoring Timeline
    res = client.get(f"/api/results/{sub_id}", headers=inst_headers)
    assert res.status_code == 200, f"Audit report failed: {res.text}"
    report = res.json()
    assert "violation_logs" in report and len(report["violation_logs"]) == 2
    assert "questions_breakdown" in report
    print(f"  [OK] Full audit report retrieved by instructor: Score {report['score']}/{report['total_points']}, {len(report['violation_logs'])} proctoring violations tracked with timestamps.")

    # 11. Test CSV Export
    print("\n[11] Verifying CSV Export for Instructors...")
    res = client.get("/api/results/export/csv", headers=inst_headers)
    assert res.status_code == 200, f"CSV export failed: {res.text}"
    assert "text/csv" in res.headers["content-type"]
    assert "Candidate Name" in res.text
    print("  [OK] Downloadable CSV results report generated successfully!")

    # 12. Test Deleting Quiz
    print("\n[12] Verifying Deletion of Quiz (Cascade Questions & Submissions)...")
    res = client.delete(f"/api/quizzes/{quiz_id}", headers=inst_headers)
    assert res.status_code == 200, f"Delete quiz failed: {res.text}"
    remaining = client.get("/api/quizzes", headers=inst_headers).json()["quizzes"]
    assert len(remaining) == 0, f"Expected 0 remaining quizzes, got {len(remaining)}"
    print("  [OK] Quiz successfully deleted with cascade and confirmed 0 quizzes remaining!")

    # Clean up test registration so database remains completely clean
    db = SessionLocal()
    db.query(User).filter(User.username == "candidate_test").delete(synchronize_session=False)
    db.commit()
    db.close()
    from app.supabase_client import get_supabase
    sb = get_supabase()
    if sb:
        sb.table("users").delete().eq("username", "candidate_test").execute()

    print("\n=======================================================")
    print("  ALL PLATFORM VERIFICATION CHECKS PASSED PERFECTLY!  ")
    print("=======================================================\n")



if __name__ == "__main__":
    test_full_platform()
