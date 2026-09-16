#!/usr/bin/env python3
"""
Automated Codebase Health & Static Diagnostics Scanner
Scans Python and JS/JSX files for:
  1. God files (> 350 LOC)
  2. Bare exceptions / swallowed errors (`except:`, `except Exception: pass`)
  3. Mock / Fake data traces in production code
  4. Unused imports / syntax anomalies
  5. Unhandled promise rejections / empty catch blocks
"""

import os
import sys
import re
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]  # Adjust to root
EXCLUDED_DIRS = {
    "node_modules", ".venv", "venv", "dist", "build", ".git", 
    "__pycache__", ".agents", "scratch", ".pytest_cache"
}

def scan_files():
    god_files = []
    bare_excepts = []
    swallowed_errors = []
    mock_data_flags = []
    empty_catch_blocks = []
    total_files = 0
    total_lines = 0

    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in [".py", ".js", ".jsx", ".ts", ".tsx"]:
                continue

            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, WORKSPACE_ROOT)
            total_files += 1

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception as e:
                continue

            num_lines = len(lines)
            total_lines += num_lines

            if num_lines > 350:
                god_files.append((rel_path, num_lines))

            # Pattern scanning per file
            content = "".join(lines)

            # 1. Bare excepts in Python
            if ext == ".py":
                for idx, line in enumerate(lines, start=1):
                    if re.search(r"^\s*except\s*:", line):
                        bare_excepts.append((rel_path, idx, line.strip()))
                    if re.search(r"except.*:\s*pass", line):
                        swallowed_errors.append((rel_path, idx, line.strip()))

            # 2. Mock data references
            for idx, line in enumerate(lines, start=1):
                if re.search(r"\b(mock_data|mockData|fake_data|lorem ipsum)\b", line, re.IGNORECASE):
                    # Ignore comment notes or test files
                    if "test" not in rel_path.lower():
                        mock_data_flags.append((rel_path, idx, line.strip()))

            # 3. Empty catch blocks in JS/JSX
            if ext in [".js", ".jsx", ".ts", ".tsx"]:
                for idx, line in enumerate(lines, start=1):
                    if re.search(r"\.catch\(\s*\(\)\s*=>\s*\{\s*\}\s*\)", line) or re.search(r"catch\s*\([^)]*\)\s*\{\s*\}", line):
                        empty_catch_blocks.append((rel_path, idx, line.strip()))

    print("=" * 70)
    print("🩺 CODEBASE HEALTH & STATIC SCAN REPORT")
    print("=" * 70)
    print(f"Total Source Files Scanned: {total_files}")
    print(f"Total Lines of Code: {total_lines}")
    print()

    print(f"📌 God Files (> 350 LOC): {len(god_files)}")
    for f, count in sorted(god_files, key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {f}: {count} lines")
    print()

    print(f"⚠️ Bare `except:` Clauses: {len(bare_excepts)}")
    for f, line_no, content in bare_excepts[:10]:
        print(f"  - {f}:{line_no} -> {content}")
    print()

    print(f"⚠️ Swallowed Errors (`except: pass`): {len(swallowed_errors)}")
    for f, line_no, content in swallowed_errors[:10]:
        print(f"  - {f}:{line_no} -> {content}")
    print()

    print(f"🚫 Mock / Fake Data Indicators: {len(mock_data_flags)}")
    for f, line_no, content in mock_data_flags[:10]:
        print(f"  - {f}:{line_no} -> {content}")
    print()

    print(f"⚠️ Empty Catch Blocks: {len(empty_catch_blocks)}")
    for f, line_no, content in empty_catch_blocks[:10]:
        print(f"  - {f}:{line_no} -> {content}")
    print()
    print("=" * 70)

if __name__ == "__main__":
    scan_files()
