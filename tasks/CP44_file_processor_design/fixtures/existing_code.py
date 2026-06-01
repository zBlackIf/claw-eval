"""Existing scattered code fragments from the project."""
import requests
import os

def call_mineru_api(pdf_path: str) -> str:
    """Send PDF to MinerU service for OCR conversion."""
    url = os.getenv("MINERU_API_URL", "http://localhost:8080/convert")
    with open(pdf_path, "rb") as f:
        resp = requests.post(url, files={"file": f}, timeout=300)
    resp.raise_for_status()
    return resp.json()["markdown"]

def extract_images_from_markdown(md_text: str, base_dir: str) -> list:
    """Extract image references from markdown text."""
    import re
    pattern = r'!\[.*?\]\((.*?)\)'
    matches = re.findall(pattern, md_text)
    return [os.path.join(base_dir, m) for m in matches if not m.startswith("http")]

def get_image_context(md_text: str, image_ref: str, context_chars: int = 500) -> str:
    """Get surrounding text context for an image in markdown."""
    idx = md_text.find(image_ref)
    if idx == -1:
        return ""
    start = max(0, idx - context_chars)
    end = min(len(md_text), idx + len(image_ref) + context_chars)
    return md_text[start:end]
