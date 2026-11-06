"""Read PDF pages and recover pages without a text layer using OCR."""

from pathlib import Path
import re

from .models import Document, Page


def extract(path: str, doc_version: str, superseded: bool) -> Document:
    source = Path(path)
    doc = Document(source.name, doc_version, superseded)
    if source.suffix.lower() == ".pdf":
        import pdfplumber
        import pytesseract
        from pdf2image import convert_from_path

        with pdfplumber.open(source) as pdf:
            for number, page in enumerate(pdf.pages, 1):
                text = page.extract_text() or ""
                needs_ocr = not text.strip()
                if needs_ocr:
                    image, = convert_from_path(path, dpi=250, first_page=number,
                                               last_page=number)
                    text = pytesseract.image_to_string(image)
                doc.pages.append(Page(source.name, number, text, needs_ocr))
        return doc

    text = source.read_text(encoding="utf-8-sig")
    if source.suffix.lower() == ".md":
        text = re.sub(r"\A---\s*\n.*?\n---[ \t]*\n", "", text, count=1, flags=re.S)
    if source.suffix.lower() == ".html":
        from bs4 import BeautifulSoup

        html = BeautifulSoup(text, "html.parser")
        for tag in html(["script", "style", "nav", "footer"]):
            tag.decompose()
        for tag in html.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
            tag.insert_before("# " + tag.get_text(" ", strip=True) + "\n")
            tag.decompose()
        text = html.get_text("\n", strip=True)
    doc.pages.append(Page(source.name, 1, text))
    return doc
