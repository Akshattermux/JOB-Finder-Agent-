import os
import yaml
from pathlib import Path
from typing import Dict, Any

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False


def load_user_profile(profile_path: str) -> Dict[str, Any]:
    """Load candidate profile from YAML file."""
    path = Path(profile_path)
    if not path.exists():
        raise FileNotFoundError(f"User profile file not found at {profile_path}")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def extract_single_resume(path_str: str) -> str:
    """Extract plain text from a single .pdf, .docx, .txt, or .md resume file."""
    if not path_str:
        return ""

    path = Path(path_str)
    if not path.exists():
        # Check if relative to BASE_DIR (workspace root)
        base_path = Path(__file__).resolve().parent.parent / path_str
        if base_path.exists():
            path = base_path
        else:
            return ""

    ext = path.suffix.lower()

    if ext == ".pdf":
        if not PYPDF_AVAILABLE:
            return f"[Error: pypdf library not available to read {path.name}]"
        try:
            reader = PdfReader(str(path))
            text_parts = []
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    text_parts.append(txt)
            raw_text = "\n".join(text_parts)
            # Ensure safe string formatting
            return raw_text.strip()
        except Exception as e:
            return f"[Error extracting PDF resume {path.name}: {e}]"

    elif ext == ".docx":
        if not DOCX_AVAILABLE:
            return f"[Error: python-docx library not available to read {path.name}]"
        try:
            doc = docx.Document(str(path))
            return "\n".join([p.text for p in doc.paragraphs if p.text])
        except Exception as e:
            return f"[Error extracting DOCX resume: {e}]"

    else:
        # Plain text / Markdown (.txt, .md, .rst, etc.)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read().strip()
        except Exception as e:
            return f"[Error reading text resume: {e}]"


def extract_resume_text(resume_path: Any) -> str:
    """Extract plain text from single or multiple resume paths."""
    if isinstance(resume_path, list):
        results = [extract_single_resume(p) for p in resume_path if p]
        return "\n\n--- NEXT RESUME DOCUMENT ---\n\n".join([r for r in results if r])
    elif isinstance(resume_path, str):
        return extract_single_resume(resume_path)
    return ""

