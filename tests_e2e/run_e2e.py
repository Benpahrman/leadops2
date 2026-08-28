"""E2E test runner script."""

import os
import sys
import subprocess
import argparse


def run_e2e_tests(
    test_file: str = None,
    headed: bool = False,
    debug: bool = False,
    base_url: str = "http://127.0.0.1:8000",
    frontend_url: str = "http://127.0.0.1:5173",
):
    """Run E2E tests with Playwright."""
    
    # Set environment variables
    env = os.environ.copy()
    env["E2E_BASE_URL"] = base_url
    env["E2E_FRONTEND_URL"] = frontend_url
    
    # Build pytest command
    cmd = [
        sys.executable, "-m", "pytest",
        "tests_e2e",
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
    ]
    
    if test_file:
        cmd.append(test_file)
    
    if headed:
        cmd.extend(["--headed", "--no-headless"])
    
    if debug:
        cmd.extend(["--headed", "--slowmo=1000"])
    
    # Add Playwright options
    cmd.extend([
        "--browser", "chromium",
        "--base-url", frontend_url,
    ])
    
    print(f"Running: {' '.join(cmd)}")
    print(f"Base URL: {base_url}")
    print(f"Frontend URL: {frontend_url}")
    
    result = subprocess.run(cmd, env=env, cwd=os.path.dirname(__file__))
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run E2E tests")
    parser.add_argument("--test", "-t", help="Specific test file to run")
    parser.add_argument("--headed", action="store_true", help="Run in headed mode")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode (slow)")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5173", help="Frontend URL")
    args = parser.parse_args()
    
    exit_code = run_e2e_tests(
        test_file=args.test,
        headed=args.headed,
        debug=args.debug,
        base_url=args.base_url,
        frontend_url=args.frontend_url,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()