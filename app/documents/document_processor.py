import csv
import json
from pathlib import Path


class DocumentProcessor:

    SUPPORTED_FORMATS = {".txt", ".md", ".json", ".csv"}

    def __init__(self, root_dir="documents", max_file_size=5 * 1024 * 1024):

        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

        self.max_file_size = max_file_size

    def _get_safe_path(self, filename):

        if not isinstance(filename, str) or not filename.strip():
            raise ValueError("Filename is required.")

        path = (self.root_dir / filename).resolve()

        if not path.is_relative_to(self.root_dir):
            raise PermissionError("File access outside documents is blocked.")

        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError("Unsupported document format.")

        return path

    def read_document(self, filename):

        path = self._get_safe_path(filename)

        if not path.is_file():
            raise FileNotFoundError("Document not found.")

        if path.stat().st_size > self.max_file_size:
            raise ValueError("Document exceeds the maximum file size.")

        suffix = path.suffix.lower()

        if suffix in {".txt", ".md"}:

            return {
                "filename": path.name,
                "format": suffix,
                "content": path.read_text(encoding="utf-8")
            }

        if suffix == ".json":

            with path.open("r", encoding="utf-8") as file:
                content = json.load(file)

            return {
                "filename": path.name,
                "format": suffix,
                "content": content
            }

        if suffix == ".csv":

            with path.open("r", encoding="utf-8", newline="") as file:
                content = list(csv.DictReader(file))

            return {
                "filename": path.name,
                "format": suffix,
                "content": content
            }

        raise ValueError("Unsupported document format.")

    def create_document(self, filename, content):

        path = self._get_safe_path(filename)

        if path.suffix.lower() not in {".txt", ".md"}:
            raise ValueError("Only TXT and Markdown creation is supported.")

        if not isinstance(content, str):
            raise ValueError("Document content must be text.")

        if len(content.encode("utf-8")) > self.max_file_size:
            raise ValueError("Document exceeds the maximum file size.")

        if path.exists():
            raise FileExistsError("Document already exists.")

        path.write_text(content, encoding="utf-8")

        return {
            "status": "created",
            "filename": path.name,
            "format": path.suffix.lower()
        }