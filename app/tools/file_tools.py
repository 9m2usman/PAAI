
from pathlib import Path


# STEP 1: Identify the PAAI project directory

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# STEP 2: Define directories and files that must stay private

EXCLUDED_DIRECTORIES = {
    "venv",
    ".venv",
    ".git",
    "__pycache__",
    "node_modules",
    ".idea",
    ".vscode"
}

EXCLUDED_FILES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_ed25519"
}


# STEP 3: List safe project files

def list_project_files():

    project_files = []

    for path in PROJECT_ROOT.rglob("*"):

        if not path.is_file():
            continue

        relative_path = path.relative_to(PROJECT_ROOT)

        if any(
            part in EXCLUDED_DIRECTORIES
            for part in relative_path.parts
        ):
            continue

        if path.name in EXCLUDED_FILES:
            continue

        if path.name.startswith(".env."):
            continue

        if path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
            continue

        project_files.append(str(relative_path))

    project_files.sort()

    # STEP 4: Return a limited result

    return {
        "project": "PAAI",
        "total_files_found": len(project_files),
        "files": project_files[:100],
        "truncated": len(project_files) > 100
    }
