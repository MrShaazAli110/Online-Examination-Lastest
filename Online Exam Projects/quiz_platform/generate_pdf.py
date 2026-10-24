import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from app.parsers import parse_uploaded_file

sample_dir = os.path.join(os.path.dirname(__file__), "sample_files")
pdf_path = os.path.join(sample_dir, "sample_quiz.pdf")

c = canvas.Canvas(pdf_path, pagesize=letter)
c.setFont("Helvetica-Bold", 14)
c.drawString(50, 750, "Full-Stack & Computer Science Online Quiz")

c.setFont("Helvetica", 11)
lines = [
    "1. Which protocol is primarily used for secure communications over the Internet?",
    "A) HTTP",
    "B) FTP",
    "C) HTTPS",
    "D) SMTP",
    "Answer: C",
    "Explanation: HTTPS provides encryption using TLS/SSL.",
    "",
    "2. In Python, what is the output of bool([])?",
    "A) True",
    "B) False",
    "C) None",
    "D) Error",
    "Answer: B",
    "Explanation: Empty sequences evaluate to False in Python.",
    "",
    "[CODING]",
    "Title: Factorial Calculation",
    "Description: Read an integer n from standard input and print n! (factorial of n).",
    "Points: 10",
    "Starter: def fact(n): return 1 if n<=1 else n*fact(n-1)",
    "Test: 5 -> 120",
    "Test: 3 -> 6",
    "Test: 1 -> 1",
]

y = 710
for line in lines:
    if line.startswith("1.") or line.startswith("2.") or line.startswith("[CODING]"):
        c.setFont("Helvetica-Bold", 11)
    else:
        c.setFont("Helvetica", 10)
    c.drawString(50, y, line)
    y -= 18

c.save()
print(f"Generated {pdf_path}")

# Test parsing the PDF
with open(pdf_path, "rb") as f:
    pdf_qs = parse_uploaded_file("sample_quiz.pdf", f.read())

print(f"Parsed {len(pdf_qs)} questions from PDF successfully:")
for q in pdf_qs:
    print(f"- Type: {q['question_type']}, Title: {q['title']}, Ans/Tests: {q.get('correct_answer') or len(q.get('test_cases', []))}")
