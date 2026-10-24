import re
import io
from docx import Document
from pypdf import PdfReader

def extract_text_from_txt(file_bytes: bytes) -> str:
    """Decodes plain text bytes with fallback encodings."""
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            return file_bytes.decode(enc)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="replace")

def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extracts all text from docx paragraphs and tables."""
    doc = Document(io.BytesIO(file_bytes))
    lines = []
    for p in doc.paragraphs:
        if p.text.strip():
            lines.append(p.text.strip())
    # Also check tables if any
    for table in doc.tables:
        for row in table.rows:
            row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_text:
                lines.append(" | ".join(row_text))
    return "\n".join(lines)

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extracts text from all pages of a PDF."""
    reader = PdfReader(io.BytesIO(file_bytes))
    lines = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            lines.append(page_text)
    return "\n".join(lines)

def parse_questions_from_text(raw_text: str) -> list[dict]:
    """
    Parses questions from raw text supporting both MCQ and Coding problems.
    Supports varied numbering formats (1., Q1., Question 1:, etc.) and option indicators (A., A), (A), [A]).
    """
    questions = []
    
    # Split text into blocks separated by multiple newlines or question markers
    # First, let's normalize line breaks
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Look for [CODING] or [CODE] blocks first
    blocks = re.split(r'\n\s*\n+', normalized)
    
    current_q = None
    lines = normalized.split("\n")
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        # Check for Coding Question Block
        if re.match(r'^\[(?:CODING|CODE|PROGRAMMING)\]', line, re.IGNORECASE):
            coding_q = {
                "question_type": "coding",
                "title": "Programming Problem",
                "description": "",
                "options": [],
                "correct_answer": "",
                "explanation": "",
                "points": 10,
                "language": "python",
                "starter_code": "def solve():\n    # Write your solution here\n    pass\n\nif __name__ == '__main__':\n    solve()",
                "test_cases": []
            }
            i += 1
            desc_lines = []
            starter_lines = []
            in_starter = False
            
            while i < len(lines):
                sub_line = lines[i].strip()
                if re.match(r'^\[(?:CODING|CODE|PROGRAMMING)\]', sub_line, re.IGNORECASE) or \
                   re.match(r'^(?:Q\d+[\.:]?|\d+[\.:])', sub_line, re.IGNORECASE):
                    # Next question begins
                    break
                
                title_match = re.match(r'^(?:Title|Problem):\s*(.+)', sub_line, re.IGNORECASE)
                pts_match = re.match(r'^(?:Points|Marks):\s*(\d+)', sub_line, re.IGNORECASE)
                starter_match = re.match(r'^(?:Starter|Template):\s*(.*)', sub_line, re.IGNORECASE)
                test_match = re.match(r'^(?:Test|Case):\s*(.*)', sub_line, re.IGNORECASE)
                
                if title_match:
                    coding_q["title"] = title_match.group(1).strip()
                    in_starter = False
                elif pts_match:
                    coding_q["points"] = int(pts_match.group(1))
                    in_starter = False
                elif starter_match:
                    in_starter = True
                    first_starter = starter_match.group(1).strip()
                    if first_starter:
                        starter_lines.append(first_starter)
                elif test_match:
                    in_starter = False
                    # Format: Test: Input: 5 -> Output: 25 or Test: In: 5 | Out: 25
                    test_str = test_match.group(1).strip()
                    t_in = ""
                    t_out = ""
                    if "->" in test_str:
                        parts = test_str.split("->")
                        t_in = parts[0].replace("Input:", "").replace("In:", "").strip()
                        t_out = parts[1].replace("Output:", "").replace("Out:", "").strip()
                    elif "|" in test_str:
                        parts = test_str.split("|")
                        t_in = parts[0].replace("Input:", "").replace("In:", "").strip()
                        t_out = parts[1].replace("Output:", "").replace("Out:", "").strip()
                    if t_in or t_out:
                        coding_q["test_cases"].append({
                            "input": t_in,
                            "expected_output": t_out,
                            "is_hidden": len(coding_q["test_cases"]) > 0
                        })
                elif in_starter:
                    starter_lines.append(lines[i])
                else:
                    desc_lines.append(sub_line)
                i += 1
            
            if starter_lines:
                coding_q["starter_code"] = "\n".join(starter_lines).strip()
            if desc_lines:
                coding_q["description"] = "\n".join(desc_lines).strip()
                if coding_q["title"] == "Programming Problem" and desc_lines:
                    coding_q["title"] = desc_lines[0][:60]
            questions.append(coding_q)
            continue

        # Check for start of a new MCQ / Standard Question: e.g., "1. ", "Q1: ", "Question 1."
        q_start_match = re.match(r'^(?:Question\s*\d+[\.:]?|Q\d+[\.:]?|\d+[\.:\)])\s*(.*)', line, re.IGNORECASE)
        
        if q_start_match:
            q_title = q_start_match.group(1).strip()
            # If title is on next line
            if not q_title and i + 1 < len(lines):
                i += 1
                q_title = lines[i].strip()
            
            mcq_q = {
                "question_type": "mcq",
                "title": q_title or f"Question {len(questions) + 1}",
                "description": "",
                "options": [],
                "correct_answer": "",
                "explanation": "",
                "points": 5,
                "starter_code": "",
                "language": "",
                "test_cases": []
            }
            
            i += 1
            # Collect additional description or options or answers
            while i < len(lines):
                sub_line = lines[i].strip()
                if not sub_line:
                    i += 1
                    continue
                
                # Check if next question starts
                if re.match(r'^(?:\[(?:CODING|CODE)\]|Question\s*\d+[\.:]?|Q\d+[\.:]?|\d+[\.:\)])', sub_line, re.IGNORECASE):
                    break
                
                # Check for Option: e.g. "A) ...", "(A) ...", "A. ...", "[A] ..."
                opt_match = re.match(r'^(?:(?:\(([A-Da-d1-4])\)|\[([A-Da-d1-4])\]|([A-Da-d1-4])[\.\)\:-]))\s*(.*)', sub_line)
                
                # Check for Answer line: "Answer: B", "Ans: (B)", "Correct Answer: B"
                ans_match = re.match(r'^(?:Answer|Ans|Correct(?:\s*Answer)?):\s*[\(\[]?([A-Da-d1-4]|.+?)[\)\]]?$', sub_line, re.IGNORECASE)
                
                # Check for Explanation line
                exp_match = re.match(r'^(?:Explanation|Reason):\s*(.*)', sub_line, re.IGNORECASE)
                
                # Check for Points line
                pts_match = re.match(r'^(?:Points|Marks):\s*(\d+)', sub_line, re.IGNORECASE)

                if ans_match:
                    ans_val = ans_match.group(1).strip().upper()
                    mcq_q["correct_answer"] = ans_val
                elif exp_match:
                    mcq_q["explanation"] = exp_match.group(1).strip()
                elif pts_match:
                    mcq_q["points"] = int(pts_match.group(1))
                elif opt_match:
                    opt_letter = (opt_match.group(1) or opt_match.group(2) or opt_match.group(3)).upper()
                    opt_text = opt_match.group(4).strip()
                    mcq_q["options"].append(f"{opt_letter}) {opt_text}")
                else:
                    # Append to question title or description
                    if not mcq_q["options"]:
                        mcq_q["title"] += " " + sub_line
                    else:
                        mcq_q["explanation"] += " " + sub_line
                i += 1
            
            # Post-process options and correct answer
            # If options were found, ensure correct answer matches
            if mcq_q["options"] and not mcq_q["correct_answer"]:
                mcq_q["correct_answer"] = "A"  # Default fallback if unspecified
            elif not mcq_q["options"]:
                # If no choices were found, treat as short answer
                mcq_q["question_type"] = "short_answer"
                
            questions.append(mcq_q)
            continue
        
        i += 1

    return questions

def parse_uploaded_file(filename: str, file_bytes: bytes) -> list[dict]:
    """Dispatches file parsing according to extension (.docx, .pdf, .txt)."""
    if not file_bytes or len(file_bytes) == 0:
        raise ValueError("The uploaded file is empty. Please select a valid document.")

    ext = filename.lower().split(".")[-1]
    if ext in ["txt", "text"]:
        text = extract_text_from_txt(file_bytes)
    elif ext in ["docx", "doc"]:
        text = extract_text_from_docx(file_bytes)
    elif ext in ["pdf"]:
        text = extract_text_from_pdf(file_bytes)
    else:
        raise ValueError(f"Unsupported file format: .{ext}. Please upload a .docx, .pdf, or .txt file.")
    
    questions = parse_questions_from_text(text)
    if not questions:
        raise ValueError("No questions could be parsed from the file. Please ensure questions follow standard format (e.g., '1. Question', 'A) Option', 'Answer: A').")
    
    return questions
