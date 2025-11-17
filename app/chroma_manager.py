# app/chroma_manager.py
"""
Gerenciamento completo do ChromaDB:
 - Criação / carregamento da coleção
 - Inserção de chunks com metadados
 - Detecção de alterações nos PDFs via hash
 - Atualização incremental (remove apenas PDFs alterados)
 - Buscas vetoriais (normal + expandida)
"""

import os
import json
import hashlib
import logging
from typing import Dict

import chromadb

from app.config import (
    CHROMA_DB_PATH,
    COLLECTION_NAME,
    PDF_FILES,
    HASH_MAP_FILE,
)
from app.embeddings import get_embedding_function
from app.pdf_loader import extract_text_from_pdf

logger = logging.getLogger("app.chroma_manager")
logger.setLevel(logging.INFO)


# ==============================================================
# Inicia o client do ChromaDB
# ==============================================================

def get_chroma_client():
    return chromadb.PersistentClient(path=CHROMA_DB_PATH)


# ==============================================================
# Hashing dos PDFs
# ==============================================================

def compute_pdf_hash(pdf_path: str) -> str:
    """Retorna o hash MD5 do PDF."""
    if not os.path.exists(pdf_path):
        return ""
    with open(pdf_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def load_hash_map() -> Dict[str, str]:
    """Carrega arquivo JSON com hashes."""
    if os.path.exists(HASH_MAP_FILE):
        try:
            with open(HASH_MAP_FILE, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}
    return {}


def save_hash_map(hash_map: Dict[str, str]):
    with open(HASH_MAP_FILE, "w", encoding="utf-8") as fh:
        json.dump(hash_map, fh, indent=2, ensure_ascii=False)


# ==============================================================
# Criar coleção
# ==============================================================

def get_or_create_collection():
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=get_embedding_function()
    )


# ==============================================================
# Remover chunks antigos
# ==============================================================

def remove_pdf_chunks(collection, pdf_name: str):
    try:
        # Não incluir "ids" aqui – Chroma não aceita isso no include
        result = collection.get(include=["metadatas"])

        ids = result.get("ids", [])
        metadatas = result.get("metadatas", [])

        # Flatten nested lists
        if isinstance(ids, list) and ids and isinstance(ids[0], list):
            ids = ids[0]
        if isinstance(metadatas, list) and metadatas and isinstance(metadatas[0], list):
            metadatas = metadatas[0]

        ids_to_delete = [
            id_
            for id_, md in zip(ids, metadatas)
            if isinstance(md, dict) and md.get("pdf_name") == pdf_name
        ]

        if ids_to_delete:
            collection.delete(ids_to_delete)
            logger.info(f"Removidos {len(ids_to_delete)} chunks antigos de {pdf_name}.")
        else:
            logger.info(f"Nenhum chunk antigo encontrado para {pdf_name}.")

    except Exception as e:
        logger.error(f"Erro ao remover chunks antigos de {pdf_name}: {e}")


# ==============================================================
# Reindexação incremental
# ==============================================================

def update_embeddings():
    hash_old = load_hash_map()
    hash_new = {}

    collection = get_or_create_collection()

    for pdf in PDF_FILES:
        logger.info(f"Verificando alterações em: {pdf}")

        current_hash = compute_pdf_hash(pdf)
        hash_new[pdf] = current_hash

        # Se o hash mudou → precisa reindexar
        if hash_old.get(pdf) != current_hash:
            logger.info(f"Alteração detectada → Reindexando {pdf}")

            # Remover chunks antigos do mesmo PDF
            remove_pdf_chunks(collection, pdf)

            # Extrair novos chunks
            docs = extract_text_from_pdf(pdf)
            if not docs:
                logger.warning(f"Nenhum texto extraído de {pdf}.")
                continue

            ids = []
            texts = []
            metadatas = []

            for i, d in enumerate(docs):
                doc_id = f"{os.path.basename(pdf)}__page{d['page_number']}__chunk{i}"

                ids.append(doc_id)
                texts.append(d["text"])

                metadatas.append({
                    "pdf_name": pdf,
                    "page_number": d["page_number"],
                    "char_start": d["char_start"],
                    "char_end": d["char_end"],
                    "contains_paren_link": d["contains_paren_link"],
                    "source_urls": "||".join(d["source_urls"]) if d["source_urls"] else ""
                })

            # Inserir no Chroma
            collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids,
            )

            logger.info(f"Reindexados {len(texts)} chunks de {pdf}")

        else:
            logger.info(f"Nenhuma alteração em {pdf}. Mantendo embeddings existentes.")

    save_hash_map(hash_new)
    logger.info("Hash map atualizado.")


# ==============================================================
# Buscar no vetor — sem 'ids'
# ==============================================================

def vector_search(collection, query: str, alt_query: str, k: int = 20):
    """
    Retorna a busca principal + expandida
    """
    try:
        res_main = collection.query(
            query_texts=[query],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        print("Erro na busca principal:", e)
        res_main = {}

    try:
        res_alt = collection.query(
            query_texts=[alt_query],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        print("Erro na busca expandida:", e)
        res_alt = {}

    return res_main, res_alt
