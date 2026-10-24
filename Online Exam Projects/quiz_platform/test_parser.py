import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.parsers import parse_questions_from_text, parse_uploaded_file
from docx import Document

sample_text = """
1. What is the time complexity of searching an element in a balanced binary search tree?
A) O(1)
B) O(log n)
C) O(n)
D) O(n log n)
Answer: B
Explanation: A balanced BST has height O(log n).

2. Which keyword is used to declare a generator in Python?
A) return
B) yield
C) produce
D) async
Answer: B
Explanation: yield creates a generator function in Python.

[CODING]
Title: Sum of Two Numbers
Description: Read two space-separated integers from stdin and output their sum.
Points: 10
Starter:
import sys
# Read two numbers and print sum
line = sys.stdin.read().strip()
if line:
    a, b = map(int, line.split())
    print(a + b)
Test: 10 25 -> 35
Test: -5 15 -> 10
Test: 100 200 -> 300
"""

qs = parse_questions_from_text(sample_text)
print(f"Parsed {len(qs)} questions successfully:")
for q in qs:
    print(f"- Type: {q['question_type']}, Title: {q['title']}, Ans/Tests: {q.get('correct_answer') or len(q.get('test_cases', []))}")

# Now generate sample .txt, .docx, and .pdf files in sample_files
sample_dir = os.path.join(os.path.dirname(__file__), "..", "sample_files")
os.makedirs(sample_dir, exist_ok=True)

# 1. Write sample_quiz.txt
txt_path = os.path.join(sample_dir, "sample_quiz.txt")
with open(txt_path, "w", encoding="utf-8") as f:
    f.write(sample_text)
print(f"Generated {txt_path}")

# 2. Write sample_quiz.docx
docx_path = os.path.join(sample_dir, "sample_quiz.docx")
doc = Document()
doc.add_heading("CS Assessment: Python & Data Structures", level=1)
for line in sample_text.strip().split("\n"):
    if line.strip():
        doc.add_paragraph(line.strip())
doc.save(docx_path)
print(f"Generated {docx_path}")

# 3. Test parsing the generated .docx
with open(docx_path, "rb") as f:
    docx_qs = parse_uploaded_file("sample_quiz.docx", f.read())
print(f"Parsed {len(docx_qs)} questions from docx file successfully!")
