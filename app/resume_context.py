"""
Loads optional resume / job-description text used to tailor generated
questions to a specific opportunity. Text can be pasted directly in the UI,
or loaded from a local .txt or .pdf file the user picks themselves -- nothing
is fetched from the network and nothing here talks to the LLM directly.
"""
from pathlib import Path

SUPPORTED_EXTENSIONS = (".txt", ".pdf")


def load_text_from_file(path: Path) -> str:
    """Read plain text or PDF text from a local file the user selected."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore").strip()

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError(
                "Reading PDF files requires the 'pypdf' package. "
                "Run: pip install pypdf (or paste the text instead)."
            ) from exc
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()

    raise ValueError(
        f"Unsupported file type '{suffix}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)} "
        "(or just paste the text directly)."
    )
