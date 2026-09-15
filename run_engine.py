#!/usr/bin/env python3
"""Root entrypoint for running the LeadOps ACS Email Engine and Warmup Worker."""

import sys
from pathlib import Path

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.email.engine import main

if __name__ == "__main__":
    main()
