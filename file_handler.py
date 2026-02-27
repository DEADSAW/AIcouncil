"""
file_handler.py — File upload processing and URL context fetching.
"""

import io
import re
import os
from pathlib import Path
from typing import Union
from urllib.parse import urlparse

from config import MAX_FILE_SIZE_MB, ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------

def _validate_url(url: str) -> None:
    """
    Raise ValueError if the URL is unsafe (non-HTTP/S, or points to a
    private/internal network address).
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Only http:// and https:// URLs are allowed. Got: {url!r}")

    hostname = parsed.hostname or ""
    # Block loopback, link-local, and private IP ranges
    _BLOCKED_HOSTNAMES = (
        "localhost",
        "127.",
        "0.0.0.0",
        "::1",
        "169.254.",   # link-local
        "10.",        # RFC-1918
        "172.",       # RFC-1918 (172.16.0.0/12)
        "192.168.",   # RFC-1918
        "fd",         # IPv6 ULA
        "fc",         # IPv6 ULA
        "metadata.google.internal",
        "169.254.169.254",  # AWS/GCP metadata
    )
    for blocked in _BLOCKED_HOSTNAMES:
        if hostname.startswith(blocked) or hostname == blocked.rstrip("."):
            raise ValueError(f"Requests to internal/private addresses are not allowed: {url!r}")


# ---------------------------------------------------------------------------
# Text extraction from uploaded files
# ---------------------------------------------------------------------------

def extract_text_from_file(filename: str,
                            file_bytes: Union[bytes, io.BytesIO]) -> str:
    """
    Extract text content from an uploaded file.
    Returns the extracted text as a string.
    Raises ValueError for unsupported or oversized files.
    """
    if isinstance(file_bytes, io.BytesIO):
        file_bytes = file_bytes.read()

    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(
            f"File '{filename}' is {size_mb:.1f} MB, which exceeds the "
            f"{MAX_FILE_SIZE_MB} MB limit."
        )

    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"File type '{suffix}' is not supported. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if suffix == ".pdf":
        return _extract_pdf(file_bytes, filename)

    # All other types: try UTF-8, fall back to latin-1
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


def _extract_pdf(file_bytes: bytes, filename: str) -> str:
    """Extract text from a PDF using PyPDF2."""
    try:
        import PyPDF2  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "PyPDF2 is required for PDF support. Run: pip install PyPDF2"
        ) from exc

    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    if not pages:
        raise ValueError(f"Could not extract any text from '{filename}'.")
    return "\n\n".join(pages)


# ---------------------------------------------------------------------------
# URL content fetching
# ---------------------------------------------------------------------------

def fetch_url_content(url: str) -> str:
    """
    Fetch the text content of a URL.
    Returns plain text (strips HTML tags for HTML pages).
    Raises ValueError for unsafe URLs.
    """
    _validate_url(url)

    try:
        import httpx
    except ImportError as exc:
        raise ImportError("httpx is required. Run: pip install httpx") from exc

    with httpx.Client(timeout=15, follow_redirects=True) as client:
        resp = client.get(url, headers={"User-Agent": "AIcouncil/1.0"})
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        text = resp.text

    if "html" in content_type:
        text = _strip_html(text)

    # Truncate very long pages
    max_chars = 20000
    if len(text) > max_chars:
        text = text[:max_chars] + f"\n\n[... content truncated at {max_chars} chars ...]"

    return text


def _strip_html(html_text: str) -> str:
    """Very simple HTML tag stripper (no external dependency required)."""
    # Remove script/style blocks (allow any characters inside the closing tag name)
    html_text = re.sub(
        r"<(script|style)[^>]*>.*?</(script|style)[^>]*>",
        " ",
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # Remove all tags
    html_text = re.sub(r"<[^>]+>", " ", html_text)
    # Collapse whitespace
    html_text = re.sub(r"\s+", " ", html_text).strip()
    return html_text


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def format_context(uploaded_files: list[dict], urls: list[str]) -> str:
    """
    Build a combined context string from uploaded files and URLs.

    `uploaded_files` is a list of {"name": str, "text": str} dicts.
    """
    parts: list[str] = []

    for f in uploaded_files:
        parts.append(f"### File: {f['name']}\n```\n{f['text']}\n```")

    for url in urls:
        try:
            content = fetch_url_content(url)
            parts.append(f"### URL: {url}\n{content}")
        except Exception:  # noqa: BLE001
            parts.append(f"### URL: {url}\n[Failed to fetch URL content]")

    return "\n\n".join(parts)
