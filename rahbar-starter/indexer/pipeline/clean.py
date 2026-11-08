"""Remove repeating margin text while retaining line and paragraph boundaries."""

import re
import unicodedata
from collections import Counter
from dataclasses import replace

from .models import Document


def clean(doc: Document) -> Document:
    pages = [unicodedata.normalize("NFKC", page.text).strip().splitlines()
             for page in doc.pages]
    margins = Counter(line.strip() for lines in pages if len(lines) >= 4
                      for line in {lines[0], lines[-1]} if line.strip())
    repeated = {line for line, count in margins.items()
                if count >= 2 and count == len(pages)
                and not re.match(r"^\s*(?:#+\s|\d+[.)]\s)", line)}
    cleaned = []
    for page, lines in zip(doc.pages, pages, strict=True):
        if lines and lines[0].strip() in repeated:
            lines = lines[1:]
        if lines and lines[-1].strip() in repeated:
            lines = lines[:-1]
        text = "\n".join(line.rstrip() for line in lines)
        cleaned.append(replace(page, text=re.sub(r"\n{3,}", "\n\n", text).strip()))
    return replace(doc, pages=cleaned)
