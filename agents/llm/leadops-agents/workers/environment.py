"""Load local environment files without printing credential values."""

from pathlib import Path

from dotenv import load_dotenv


def load_local_environment() -> None:
    """Load project and workspace `.env` files when present."""
    project_dir = Path(__file__).resolve().parents[1]
    workspace_dir = project_dir.parents[2]
    load_dotenv(project_dir / ".env")
    load_dotenv(workspace_dir / ".env")