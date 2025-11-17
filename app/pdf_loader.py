# app/pdf_loader.py

import fitz
from app.config import CHUNK_SIZE, CHUNK_OVERLAP
from app.utils import extract_urls, contains_paren_link


def extract_text_from_pdf(pdf_path):
    """
    Lê o PDF e retorna uma lista de dicionários contendo:
    - texto do chunk
    - página
    - metadados (links, intervalo de caracteres)
    """
    chunks = []

    with fitz.open(pdf_path) as doc:
        for page_number, page in enumerate(doc, start=1):
            text = page.get_text().strip()

            if not text:
                continue

            start = 0
            while start < len(text):
                end = start + CHUNK_SIZE
                chunk_text = text[start:end]

                urls = extract_urls(chunk_text)

                chunks.append({
                    "pdf_name": pdf_path,
                    "page_number": page_number,
                    "text": chunk_text,
                    "char_start": start,
                    "char_end": end,
                    "contains_paren_link": contains_paren_link(chunk_text),
                    "source_urls": urls,
                })

                start = end - CHUNK_OVERLAP

    return chunks
