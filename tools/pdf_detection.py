"""PDF detection utilities.

Provides a small heuristic to determine whether a PDF is digital (text-extractable)
or scanned (image-only), which is useful to short-circuit processing paths that
don't support OCR.

The heuristic checks how many pages return text from the PDF reader and also
inspects page resources for XObject images. If very few pages contain text and
many pages have images, we treat the PDF as scanned.
"""

from pypdf import PdfReader
from pathlib import Path


def is_scanned(pdf_path: str) -> bool:
    """Return True when PDF appears scanned (image-only), else False.

    Args:
        pdf_path: Path to the PDF file to inspect.

    Heuristic summary:
      - Count pages that return non-empty text from PdfReader.extract_text().
      - Check page resources for XObject streams (commonly used for embedded images).
      - If the document has no pages, or no pages with text but some with images,
        or fewer than 20% of pages contain text, classify as scanned.
    """
    pdf_path = Path(pdf_path)
    reader = PdfReader(str(pdf_path))

    pages_with_text = 0
    pages = len(reader.pages)
    image_pages = 0

    for page in reader.pages:
        # Try to extract text from the page. If non-empty, mark as text page.
        text = None
        try:
            text = page.extract_text()
        except Exception:
            text = None

        if text and text.strip():
            pages_with_text += 1

        # Detect presence of XObject images via page Resources.
        # We defensively access the resources since PDF pages can have varied structure.
        has_image = False
        try:
            resources = page.get('/Resources') or {}
            # /XObject is commonly present when images are embedded.
            xobj = None
            if isinstance(resources, dict):
                xobj = resources.get('/XObject') or resources.get('/XObject')
            if xobj:
                has_image = True
        except Exception:
            # If anything goes wrong inspecting resources, skip image detection for this page.
            has_image = False

        if has_image:
            image_pages += 1

    # Decision rules
    if pages == 0:
        # Empty PDF — treat conservatively as scanned/unsupported
        return True

    if pages_with_text == 0 and image_pages > 0:
        return True

    # If fewer than 20% of pages have text, treat as scanned to avoid false positives
    try:
        if pages_with_text / pages < 0.2:
            return True
    except Exception:
        # Avoid division errors — default to scanned
        return True

    return False


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print('Usage: python pdf_detection.py file.pdf')
        raise SystemExit(1)

    p = sys.argv[1]
    print(is_scanned(p))
