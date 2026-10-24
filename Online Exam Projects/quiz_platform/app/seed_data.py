from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import User, Quiz, Question, Submission
from .auth import hash_password

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # Check if admin already exists
    if db.query(User).filter(User.username == "admin").first():
        db.close()
        return

    print("Seeding initial database with users, quizzes, and proctoring data...")

    # 1. Users
    admin = User(
        username="admin",
        email="admin@platform.com",
        password_hash=hash_password("admin123"),
        full_name="System Administrator",
        role="admin"
    )
    instructor = User(
        username="instructor",
        email="instructor@university.edu",
        password_hash=hash_password("prof123"),
        full_name="Prof. Alex Reynolds",
        role="instructor"
    )
    student1 = User(
        username="student1",
        email="emma@student.edu",
        password_hash=hash_password("user123"),
        full_name="Emma Watson",
        role="student"
    )
    student2 = User(
        username="student2",
        email="david@student.edu",
        password_hash=hash_password("user123"),
        full_name="David Miller",
        role="student"
    )

    db.add_all([admin, instructor, student1, student2])
    db.commit()
    db.refresh(admin)
    db.refresh(instructor)
    db.refresh(student1)
    db.refresh(student2)

    # 2. Quiz 1: Python Core & Algorithm Assessment
    quiz1 = Quiz(
        title="Python Core & Algorithms Assessment",
        description="Comprehensive technical exam covering Python memory model, algorithmic complexity, and live coding challenges with proctored tab-switch monitoring.",
        code="PYTHON-101",
        instructor_id=instructor.id,
        duration_minutes=25,
        max_violations=3,
        is_active=True
    )
    db.add(quiz1)
    db.commit()
    db.refresh(quiz1)

    # Questions for Quiz 1
    q1_1 = Question(
        quiz_id=quiz1.id,
        question_type="mcq",
        title="What is the time complexity of lookup in a Python dictionary on average?",
        description="Consider standard hash table implementation with CPython.",
        correct_answer="A",
        points=5,
        order_idx=1,
        explanation="Python dictionaries are implemented as hash tables with open addressing, yielding O(1) average lookup time."
    )
    q1_1.set_options([
        "A) O(1)",
        "B) O(log n)",
        "C) O(n)",
        "D) O(n log n)"
    ])

    q1_2 = Question(
        quiz_id=quiz1.id,
        question_type="mcq",
        title="Which of the following creates a deep copy in Python?",
        description="Choose the standard library mechanism.",
        correct_answer="C",
        points=5,
        order_idx=2,
        explanation="copy.deepcopy() recursively copies all nested composite objects."
    )
    q1_2.set_options([
        "A) list.copy()",
        "B) dict.copy()",
        "C) copy.deepcopy()",
        "D) slice operator [:]"
    ])

    q1_3 = Question(
        quiz_id=quiz1.id,
        question_type="coding",
        title="Palindrome Number Checker",
        description="Write a python program that reads an integer `n` from standard input and prints `True` if it is a palindrome, otherwise `False`.\n\nA palindrome reads the same backwards as forwards (e.g. 121 -> True, -121 -> False, 10 -> False).",
        points=15,
        order_idx=3,
        language="python",
        starter_code="import sys\n\ndef is_palindrome(s: str) -> bool:\n    # Return True if s is a palindrome\n    return s == s[::-1]\n\nif __name__ == '__main__':\n    inp = sys.stdin.read().strip()\n    if inp:\n        print(is_palindrome(inp))\n"
    )
    q1_3.set_test_cases([
        {"input": "121", "expected_output": "True", "is_hidden": False},
        {"input": "-121", "expected_output": "False", "is_hidden": False},
        {"input": "10", "expected_output": "False", "is_hidden": True},
        {"input": "12321", "expected_output": "True", "is_hidden": True},
        {"input": "7", "expected_output": "True", "is_hidden": True}
    ])

    q1_4 = Question(
        quiz_id=quiz1.id,
        question_type="coding",
        title="Array Element Multiplier",
        description="Read an integer `multiplier` on line 1, and space-separated integers on line 2.\nPrint the multiplied numbers separated by spaces.",
        points=15,
        order_idx=4,
        language="python",
        starter_code="import sys\n\nlines = sys.stdin.read().strip().split('\\n')\nif len(lines) >= 2:\n    m = int(lines[0].strip())\n    nums = [int(x) * m for x in lines[1].split()]\n    print(' '.join(map(str, nums)))\n"
    )
    q1_4.set_test_cases([
        {"input": "2\n1 2 3 4", "expected_output": "2 4 6 8", "is_hidden": False},
        {"input": "3\n5 10 15", "expected_output": "15 30 45", "is_hidden": False},
        {"input": "0\n10 20 30", "expected_output": "0 0 0", "is_hidden": True}
    ])

    db.add_all([q1_1, q1_2, q1_3, q1_4])
    db.commit()

    # 3. Quiz 2: Full-Stack Web Architecture Challenge
    quiz2 = Quiz(
        title="Web Architecture & Data Structures Challenge",
        description="Test your understanding of HTTP protocols, database indexing, caching strategies, and data structures.",
        code="WEB-CS-202",
        instructor_id=instructor.id,
        duration_minutes=30,
        max_violations=3,
        is_active=True
    )
    db.add(quiz2)
    db.commit()
    db.refresh(quiz2)

    q2_1 = Question(
        quiz_id=quiz2.id,
        question_type="mcq",
        title="What HTTP status code is returned for an unauthorized authentication error?",
        description="",
        correct_answer="B",
        points=5,
        order_idx=1,
        explanation="401 Unauthorized indicates that the request has not been applied because it lacks valid authentication credentials."
    )
    q2_1.set_options([
        "A) 400 Bad Request",
        "B) 401 Unauthorized",
        "C) 403 Forbidden",
        "D) 404 Not Found"
    ])

    q2_2 = Question(
        quiz_id=quiz2.id,
        question_type="mcq",
        title="Which data structure operates on a First-In-First-Out (FIFO) basis?",
        description="",
        correct_answer="B",
        points=5,
        order_idx=2,
        explanation="A Queue operates in FIFO order."
    )
    q2_2.set_options([
        "A) Stack",
        "B) Queue",
        "C) Heap",
        "D) Binary Search Tree"
    ])

    q2_3 = Question(
        quiz_id=quiz2.id,
        question_type="coding",
        title="Even Numbers Filter",
        description="Read space-separated integers from stdin and output only the even numbers, separated by spaces. If none, output empty line.",
        points=10,
        order_idx=3,
        language="python",
        starter_code="import sys\n\ns = sys.stdin.read().strip()\nif s:\n    evens = [x for x in s.split() if int(x) % 2 == 0]\n    print(' '.join(evens))\n"
    )
    q2_3.set_test_cases([
        {"input": "1 2 3 4 5 6", "expected_output": "2 4 6", "is_hidden": False},
        {"input": "11 13 15", "expected_output": "", "is_hidden": False},
        {"input": "100 201 302", "expected_output": "100 302", "is_hidden": True}
    ])

    db.add_all([q2_1, q2_2, q2_3])
    db.commit()

    # 4. Seed an example submission from student1 to demonstrate results view & proctoring audit log
    sub1 = Submission(
        quiz_id=quiz1.id,
        user_id=student1.id,
        started_at=datetime.utcnow() - timedelta(minutes=20),
        submitted_at=datetime.utcnow() - timedelta(minutes=2),
        is_completed=True,
        score=35.0,
        total_points=40.0,
        percentage=87.5,
        status="submitted",
        violation_count=2
    )
    sub1.set_answers({
        str(q1_1.id): "A",
        str(q1_2.id): "C",
        str(q1_3.id): "import sys\ndef is_palindrome(s):\n    return s == s[::-1]\nif __name__ == '__main__':\n    inp = sys.stdin.read().strip()\n    print(is_palindrome(inp))\n",
        str(q1_4.id): "import sys\nlines = sys.stdin.read().strip().split('\\n')\nm = int(lines[0])\nprint(' '.join(str(int(x)*m) for x in lines[1].split()))\n"
    })
    sub1.set_coding_results({
        str(q1_3.id): {"passed": 5, "total": 5, "all_passed": True},
        str(q1_4.id): {"passed": 3, "total": 3, "all_passed": True}
    })
    sub1.add_violation("tab_switch", "User navigated away from active quiz tab to another browser tab.")
    sub1.add_violation("mouse_left_window", "Cursor moved outside the proctored viewport boundary.")
    
    db.add(sub1)
    db.commit()
    db.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
