import sys
import subprocess
import time
import re
import tempfile
import os

DISALLOWED_PATTERNS = [
    r"\bimport\s+subprocess\b",
    r"\bfrom\s+subprocess\b",
    r"\bimport\s+shutil\b",
    r"\bshutil\.rmtree\b",
    r"\bos\.system\b",
    r"\bos\.remove\b",
    r"\bos\.unlink\b",
    r"\bos\.rmdir\b",
    r"\bimport\s+socket\b",
    r"\bimport\s+urllib\b",
    r"\bimport\s+requests\b",
    r"\bimport\s+http\b",
    r"\bimport\s+ctypes\b",
    r"\b__import__\(['\"]subprocess['\"]\)",
    r"\b__import__\(['\"]os['\"]\)\.system",
    r"\b__import__\(['\"]socket['\"]\)",
]

def check_code_safety(code: str) -> tuple[bool, str]:
    """Basic security check to block hazardous operations in code."""
    for pattern in DISALLOWED_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"Security Violation: Restricted module or call detected ({pattern})"
    return True, ""

def _execute_in_process(code: str, test_input: str, timeout_sec: float = 3.0) -> tuple[str, str, int, bool]:
    """Fallback runner for serverless execution where OS subprocess spawning may be restricted."""
    import io
    import sys
    import threading

    old_stdin, old_stdout, old_stderr = sys.stdin, sys.stdout, sys.stderr
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    in_buf = io.StringIO(test_input or "")

    sys.stdin = in_buf
    sys.stdout = out_buf
    sys.stderr = err_buf

    err_msg = ""
    exit_code = 0
    timed_out = False

    def target():
        nonlocal err_msg, exit_code
        try:
            local_vars = {"__name__": "__main__"}
            exec(code, local_vars)
        except SystemExit as se:
            exit_code = se.code if isinstance(se.code, int) else 0
        except Exception as ex:
            err_msg = str(ex)
            exit_code = 1

    t = threading.Thread(target=target)
    t.daemon = True
    t.start()
    t.join(timeout_sec)

    if t.is_alive():
        timed_out = True
        err_msg = f"Execution exceeded {timeout_sec} seconds limit."

    sys.stdin, sys.stdout, sys.stderr = old_stdin, old_stdout, old_stderr

    stdout_res = out_buf.getvalue()
    stderr_res = err_buf.getvalue()
    if err_msg and err_msg not in stderr_res:
        stderr_res = (stderr_res + "\n" + err_msg).strip()

    return stdout_res, stderr_res, exit_code, timed_out

def execute_single_case(code: str, test_input: str, expected_output: str, timeout_sec: float = 3.0) -> dict:
    """Executes code with given stdin and compares stdout with expected_output."""
    safe, reason = check_code_safety(code)
    if not safe:
        return {
            "passed": False,
            "status": "Security Error",
            "error": reason,
            "stdout": "",
            "expected": expected_output,
            "runtime_ms": 0
        }

    # Write code to a temporary file
    temp_dir = tempfile.gettempdir()
    temp_file = os.path.join(temp_dir, f"sol_{os.getpid()}_{time.time_ns()}.py")

    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception:
        # If filesystem writing fails, use in-process execution directly
        start_time = time.time()
        stdout_data, stderr_data, exit_code, timed_out = _execute_in_process(code, test_input, timeout_sec)
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        if timed_out:
            return {"passed": False, "status": "Time Limit Exceeded", "error": stderr_data, "stdout": "", "expected": expected_output, "runtime_ms": elapsed_ms}
        norm_actual = "\n".join(line.rstrip() for line in stdout_data.strip().splitlines())
        norm_expected = "\n".join(line.rstrip() for line in (expected_output or "").strip().splitlines())
        if exit_code != 0:
            return {"passed": False, "status": "Runtime Error", "error": stderr_data, "stdout": stdout_data.strip(), "expected": expected_output, "runtime_ms": elapsed_ms}
        passed = (norm_actual == norm_expected)
        return {"passed": passed, "status": "Passed" if passed else "Wrong Answer", "stdout": norm_actual, "expected": norm_expected, "error": "", "runtime_ms": elapsed_ms}

    start_time = time.time()
    try:
        proc = None
        use_fallback = False
        try:
            proc = subprocess.Popen(
                [sys.executable, "-I", temp_file],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
        except (PermissionError, FileNotFoundError, OSError):
            use_fallback = True

        if use_fallback:
            stdout_data, stderr_data, exit_code, timed_out = _execute_in_process(code, test_input, timeout_sec)
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            if timed_out:
                return {"passed": False, "status": "Time Limit Exceeded", "error": stderr_data, "stdout": "", "expected": expected_output, "runtime_ms": elapsed_ms}
            return_code = exit_code
        else:
            try:
                stdout_data, stderr_data = proc.communicate(input=test_input or "", timeout=timeout_sec)
                elapsed_ms = round((time.time() - start_time) * 1000, 2)
                return_code = proc.returncode
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                return {
                    "passed": False,
                    "status": "Time Limit Exceeded",
                    "error": f"Execution exceeded {timeout_sec} seconds limit.",
                    "stdout": "",
                    "expected": expected_output,
                    "runtime_ms": round(timeout_sec * 1000, 2)
                }
        # Normalize stdout and expected
        norm_actual = "\n".join(line.rstrip() for line in stdout_data.strip().splitlines())
        norm_expected = "\n".join(line.rstrip() for line in (expected_output or "").strip().splitlines())

        if return_code != 0:
            return {
                "passed": False,
                "status": "Runtime Error",
                "error": stderr_data.strip(),
                "stdout": stdout_data.strip(),
                "expected": expected_output,
                "runtime_ms": elapsed_ms
            }

        passed = (norm_actual == norm_expected)
        return {
            "passed": passed,
            "status": "Passed" if passed else "Wrong Answer",
            "stdout": norm_actual,
            "expected": norm_expected,
            "error": "",
            "runtime_ms": elapsed_ms
        }

    except Exception as e:
        return {
            "passed": False,
            "status": "System Error",
            "error": str(e),
            "stdout": "",
            "expected": expected_output,
            "runtime_ms": 0
        }
    finally:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass

def run_all_test_cases(code: str, test_cases: list[dict], run_hidden: bool = True) -> dict:
    """Runs code through a list of test cases."""
    results = []
    total_count = 0
    passed_count = 0

    for i, tc in enumerate(test_cases):
        is_hidden = tc.get("is_hidden", False)
        if is_hidden and not run_hidden:
            continue
            
        total_count += 1
        test_in = tc.get("input", "")
        # Automatically normalize escaped newlines like '\n' if present as literal string
        if isinstance(test_in, str) and "\\n" in test_in and "\n" not in test_in:
            test_in = test_in.replace("\\n", "\n")
            
        test_exp = tc.get("expected_output", "")
        if isinstance(test_exp, str) and "\\n" in test_exp and "\n" not in test_exp:
            test_exp = test_exp.replace("\\n", "\n")
        
        res = execute_single_case(code, test_in, test_exp)
        res["case_number"] = i + 1
        res["is_hidden"] = is_hidden
        
        # If it's a hidden test case and failed, mask exact input/expected for anti-cheat
        if is_hidden and not res["passed"]:
            res_report = {
                "case_number": i + 1,
                "is_hidden": True,
                "passed": False,
                "status": res["status"],
                "runtime_ms": res["runtime_ms"],
                "error": res["error"] if res["status"] in ["Runtime Error", "Security Error", "Time Limit Exceeded"] else "",
                "stdout": "[Hidden Test Case]",
                "expected": "[Hidden Test Case]"
            }
        else:
            res_report = {
                "case_number": i + 1,
                "is_hidden": is_hidden,
                "passed": res["passed"],
                "status": res["status"],
                "runtime_ms": res["runtime_ms"],
                "error": res["error"],
                "stdout": res["stdout"],
                "expected": res["expected"]
            }

        if res["passed"]:
            passed_count += 1
            
        results.append(res_report)

    all_passed = (passed_count == total_count and total_count > 0)
    score_ratio = (passed_count / total_count) if total_count > 0 else 0.0

    return {
        "all_passed": all_passed,
        "total": total_count,
        "passed": passed_count,
        "score_ratio": score_ratio,
        "results": results
    }
