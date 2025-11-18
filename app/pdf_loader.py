# app/pdf_loader.py (VERSÃO SILENCIOSA)

import logging
import os
from PyPDF2 import PdfReader

from app.config import CHUNK_SIZE, CHUNK_OVERLAP
from app.utils import extract_urls, contains_paren_link, normalize_whitespace

logger = logging.getLogger("app.pdf_loader")
logger.setLevel(logging.INFO) # Deixamos o logger de ERRO, mas tiramos os PRINTs


def extract_text_from_pdf(pdf_path: str):
    """
    Extração leve usando PyPDF2.
    Versão silenciosa, sem prints de debug.
    """
    chunks = []

    abs_path = os.path.abspath(pdf_path)

    if not os.path.exists(abs_path):
        logger.error(f"[PDF] Não encontrado: {abs_path}")
        return chunks

    try:
        reader = PdfReader(abs_path)
        num_pages = len(reader.pages)
    except Exception as e:
        logger.error(f"[PDF] Erro ao abrir PDF: {e}")
        return chunks

    total_chunks = 0

    for page_number in range(num_pages):
        try:
            page = reader.pages[page_number]
            raw_text = page.extract_text() or ""
            text = normalize_whitespace(raw_text)

            text_size = len(text)

            if not text:
                continue

            start = 0
            text_len = len(text)
            
            step = CHUNK_SIZE - CHUNK_OVERLAP
            if step <= 0:
                step = CHUNK_SIZE

            while start < text_len:
                end = min(start + CHUNK_SIZE, text_len)
                chunk_text = text[start:end]

                urls = extract_urls(chunk_text)

                chunks.append({
                    "pdf_name": pdf_path,
                    "page_number": page_number + 1,
                    "text": chunk_text,
                    "char_start": start,
                    "char_end": end,
                    "contains_paren_link": contains_paren_link(chunk_text),
                    "source_urls": "||".join(urls),
                })

                total_chunks += 1

                if end == text_len:
                    break 

                start += step 

        except Exception as e:
            # Mantemos o print de ERRO de página
            print(f"[PDF DEBUG] Erro na página {page_number+1}: {e}")
            continue

    # O único print que deixamos é o total final
    print(f"    -> {len(chunks)} chunks extraídos.")
    return chunks