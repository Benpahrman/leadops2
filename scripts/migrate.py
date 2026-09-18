#!/usr/bin/env python
"""Run database migrations using Alembic."""

import subprocess
import sys
import os

def run_migrations():
    """Apply all pending migrations."""
    agents_dir = os.path.dirname(os.path.abspath(__file__))
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=agents_dir,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Migration failed: {result.stderr}")
        return False
    print(result.stdout)
    return True

def create_migration(message: str):
    """Create a new migration file."""
    agents_dir = os.path.dirname(os.path.abspath(__file__))
    result = subprocess.run(
        ["alembic", "revision", "--autogenerate", "-m", message],
        cwd=agents_dir,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Migration creation failed: {result.stderr}")
        return False
    print(result.stdout)
    return True

def show_history():
    """Show migration history."""
    agents_dir = os.path.dirname(os.path.abspath(__file__))
    result = subprocess.run(
        ["alembic", "history", "--verbose"],
        cwd=agents_dir,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    return result.returncode == 0

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Manage database migrations")
    parser.add_argument("command", choices=["upgrade", "create", "history"], help="Command to run")
    parser.add_argument("-m", "--message", help="Migration message (for create)")
    args = parser.parse_args()

    if args.command == "upgrade":
        success = run_migrations()
        sys.exit(0 if success else 1)
    elif args.command == "create":
        if not args.message:
            print("Error: --message required for create command")
            sys.exit(1)
        success = create_migration(args.message)
        sys.exit(0 if success else 1)
    elif args.command == "history":
        show_history()