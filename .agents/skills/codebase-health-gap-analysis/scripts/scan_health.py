#!/usr/bin/env python3
"""
Automated Codebase Health & Static Diagnostics Scanner
Scans Python and JS/JSX files for:
  1. God files (> 350 LOC)
  2. Bare exceptions / swallowed errors (`except:`, `except Exception: pass`)
  3. Mock / Fake data traces in production code
  4. Empty catch blocks in frontend code
"""

import os
import sys
import re
from pathlib import Path

# Fix stdout encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]

EXCLUDED_DIRS = {
    "node_modules", ".venv", "venv", "dist", "build", ".git", 
    "__pycache__", ".agents", "scratch", ".pytest_cache",
    "output", "runs", "backups", "build_artifacts", "swa-deploy",
    ".github", ".vscode", "docs"
}

def scan_files():
    god_files = []
    bare_excepts = []
    swallowed_errors = []
    mock_data_flags = []
    empty_catch_blocks = []
    total_files = 0
    total_lines = 0
    py_files = 0
    js_files = 0

    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in [".py", ".js", ".jsx", ".ts", ".tsx"]:
                continue

            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, WORKSPACE_ROOT)
            
            is_test = "test" in rel_path.lower() or "conftest" in rel_path.lower()

            total_files += 1
            if ext == ".py":
                py_files += 1
            else:
                js_files += 1

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                continue

            num_lines = len(lines)
            total_lines += num_lines

            if num_lines > 350:
                god_files.append((rel_path, num_lines))

            # Line-by-line scanning
            for idx, line in enumerate(lines, start=1):
                if ext == ".py":
                    if re.search(r"^\s*except\s*:", line):
                        bare_excepts.append((rel_path, idx, line.strip()))
                    if re.search(r"except.*:\s*pass\b", line):
                        swallowed_errors.append((rel_path, idx, line.strip()))

                if not is_test:
                    if re.search(r"\b(mock_data|mockData|fake_data)\b", line, re.IGNORECASE):
                        mock_data_flags.append((rel_path, idx, line.strip()))

                if ext in [".js", ".jsx", ".ts", ".tsx"]:
                    if re.search(r"\.catch\(\s*\(\)\s*=>\s*\{\s*\}\s*\)", line) or re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", line):
                        empty_catch_blocks.append((rel_path, idx, line.strip()))

    print("=" * 75)
    print("CODEBASE HEALTH & STATIC DIAGNOSTIC METRICS")
    print("=" * 75)
    print(f"Total Source Files: {total_files} (Python: {py_files}, JS/JSX: {js_files})")
    print(f"Total Source LOC:   {total_lines}")
    print()

    print(f"God Files (> 350 LOC) [Count: {len(god_files)}]:")
    for f, count in sorted(god_files, key=lambda x: x[1], reverse=True)[:15]:
        print(f"  - {f}: {count} lines")
    print()

    print(f"Bare `except:` Clauses [Count: {len(bare_excepts)}]:")
    for f, line_no, content in bare_excepts[:10]:
        print(f"  - {f}:{line_no} -> {content}")
    if len(bare_excepts) > 10:
        print(f"  ... and {len(bare_excepts) - 10} more.")
    print()

    print(f"Swallowed Errors (`except ...: pass`) [Count: {len(swallowed_errors)}]:")
    for f, line_no, content in swallowed_errors[:10]:
        print(f"  - {f}:{line_no} -> {content}")
    if len(swallowed_errors) > 10:
        print(f"  ... and {len(swallowed_errors) - 10} more.")
    print()

    print(f"Production Mock / Fake Data Indicators [Count: {len(mock_data_flags)}]:")
    for f, line_no, content in mock_data_flags[:10]:
        print(f"  - {f}:{line_no} -> {content}")
    if len(mock_data_flags) > 10:
        print(f"  ... and {len(mock_data_flags) - 10} more.")
    print()

    print(f"Empty Catch Blocks (Frontend) [Count: {len(empty_catch_blocks)}]:")
    for f, line_no, content in empty_catch_blocks[:10]:
        print(f"  - {f}:{line_no} -> {content}")
    print()
    print("=" * 75)

if __name__ == "__main__":
    scan_files()
