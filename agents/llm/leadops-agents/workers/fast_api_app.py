"""FastAPI application entrypoint for LeadOps Agent Server and Web Portal."""

import sys
from pathlib import Path

# Add project root to sys.path if running standalone inside container
root_path = Path(__file__).resolve().parent.parent.parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from agents.api import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
