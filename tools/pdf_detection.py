from pypdf import PdfReader
from pathlib import Path


def is_scanned(pdf_path: str) -> bool:
    """Return True if PDF appears to be scanned (image-only) or False if digital text present.

    Heuristic: if most pages return empty text from PdfReader.extract_text(), and
    page resources contain XObject images, treat as scanned.
    """
    pdf_path = Path(pdf_path)
    reader = PdfReader(str(pdf_path))
    pages_with_text = 0
    pages = len(reader.pages)
    image_pages = 0

    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            pages_with_text += 1

        # detect image XObjects in /Resources
        try:
            resources = page.get('/Resources') or {}
        except Exception:
            resources = {}
        has_image = False
        if resources:
            xobj = resources.get('/XObject') or resources.get('/XObject')
            if xobj:
                has_image = True
        if has_image:
            image_pages += 1

    # If very few pages have text but many pages have images, it's scanned.
    if pages == 0:
        return True
    if pages_with_text == 0 and image_pages > 0:
        return True
    # if less than 20% of pages have text, treat as scanned
    if pages_with_text / pages < 0.2:
        return True
    return False


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python pdf_detection.py file.pdf')
        raise SystemExit(1)
    p = sys.argv[1]
    print(is_scanned(p))
