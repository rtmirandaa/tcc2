# app/chroma_manager.py (VERSÃO COM 5 ETAPAS)
"""
Gerenciamento do ChromaDB.
"""

import os
import json
import hashlib
import logging
from typing import Dict, List, Any

import chromadb
from tqdm import tqdm

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


# -----------------------------------------------------------
# Cliente do ChromaDB
# -----------------------------------------------------------
def get_chroma_client():
    try:
        abs_path = os.path.abspath(CHROMA_DB_PATH)
        client = chromadb.PersistentClient(path=abs_path)
        return client
    except Exception as e:
        logger.error(f"Erro ao iniciar ChromaDB em '{CHROMA_DB_PATH}': {e}")
        raise


# -----------------------------------------------------------
# Hashing de PDFs
# -----------------------------------------------------------
def compute_pdf_hash(pdf_path: str) -> str:
    abs_path = os.path.abspath(pdf_path)
    if not os.path.exists(abs_path):
        logger.error(f"Arquivo PDF não encontrado: {abs_path}")
        return ""
    try:
        with open(abs_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        logger.error(f"Erro ao calcular hash de '{pdf_path}': {e}")
        return ""


def load_hash_map() -> Dict[str, str]:
    if os.path.exists(HASH_MAP_FILE):
        try:
            with open(HASH_MAP_FILE, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}
    return {}


def save_hash_map(hash_map: Dict[str, str]):
    try:
        with open(HASH_MAP_FILE, "w", encoding="utf-8") as fh:
            json.dump(hash_map, fh, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erro ao salvar hash map '{HASH_MAP_FILE}': {e}")


# -----------------------------------------------------------
# Obter ou criar coleção
# -----------------------------------------------------------
def get_or_create_collection():
    client = get_chroma_client()
    try:
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=get_embedding_function()
        )
        return collection
    except Exception as e:
        logger.error(f"Erro ao criar/abrir coleção '{COLLECTION_NAME}': {e}")
        raise


# -----------------------------------------------------------
# Remover chunks de um PDF específico
# -----------------------------------------------------------
def remove_pdf_chunks(collection, pdf_name: str):
    try:
        result = collection.get(include=["metadatas"])
        ids = result.get("ids", [])
        metadatas = result.get("metadatas", [])

        if ids and isinstance(ids[0], list):
            ids = ids[0]
        if metadatas and isinstance(metadatas[0], list):
            metadatas = metadatas[0]

        ids_to_delete = [
            _id for _id, md in zip(ids, metadatas)
            if isinstance(md, dict) and md.get("pdf_name") == pdf_name
        ]

        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            # print(f"    -> Removidos {len(ids_to_delete)} chunks antigos.") # Opcional
    except Exception as e:
        logger.error(f"Erro ao remover chunks de '{pdf_name}': {e}")


# -----------------------------------------------------------
# Atualização incremental (COM AS 5 ETAPAS)
# -----------------------------------------------------------
def update_embeddings():
    
    print("\n--- Iniciando verificação do banco de dados (RAG) ---")

    print("Etapa 1/5: Carregando hashes...")
    old_hashes = load_hash_map()
    new_hashes = {}
    
    print("Etapa 2/5: Abrindo coleção no ChromaDB...")
    collection = get_or_create_collection()

    import gc
    pdf_atualizado = False

    for pdf in PDF_FILES:
        print(f"Etapa 3/5: Verificando PDF '{os.path.basename(pdf)}'...")
        current_hash = compute_pdf_hash(pdf)
        new_hashes[pdf] = current_hash

        if not current_hash:
            continue

        if old_hashes.get(pdf) == current_hash:
            print("    -> PDF sem modificações.")
            continue

        # Se chegou aqui, o PDF mudou
        pdf_atualizado = True
        print(f"Etapa 4/5: PDF modificado. Extraindo texto...")
        docs = extract_text_from_pdf(pdf)

        if not docs:
            print("    -> Nenhum texto extraído.")
            continue

        print(f"Etapa 5/5: Indexando {len(docs)} chunks (isso pode demorar)...")
        remove_pdf_chunks(collection, pdf) # Limpa chunks antigos

        BATCH_SIZE = 5 # (Pequeno para não travar o Ollama)
        batch_docs = []
        batch_ids = []
        batch_metas = []
        count = 0

        # Usamos tqdm aqui para ter uma barra de progresso!
        for i, d in tqdm(enumerate(docs), total=len(docs), desc="    -> Indexando"):
            doc_id = (
                f"{os.path.basename(pdf)}__page{d['page_number']}__chunk{i}"
            )

            batch_docs.append(d["text"])
            batch_ids.append(doc_id)
            batch_metas.append({
                "pdf_name": pdf,
                "page_number": d["page_number"],
                "char_start": d["char_start"],
                "char_end": d["char_end"],
                "contains_paren_link": d["contains_paren_link"],
                "source_urls": d["source_urls"] # Já deve ser '||' do loader
            })

            if len(batch_docs) == BATCH_SIZE:
                collection.add(
                    documents=batch_docs,
                    ids=batch_ids,
                    metadatas=batch_metas
                )
                count += len(batch_docs)
                batch_docs.clear()
                batch_ids.clear()
                batch_metas.clear()
                gc.collect() 

        # enviar o resto
        if batch_docs:
            collection.add(
                documents=batch_docs,
                ids=batch_ids,
                metadatas=batch_metas
            )
            count += len(batch_docs)
            gc.collect()

        print(f"    -> {count} chunks indexados com sucesso.")

    if not pdf_atualizado:
        print("Etapa 3/5: Verificação concluída. Nenhum PDF modificado.")
        print("Etapa 4/5: Pulada.")
        print("Etapa 5/5: Pulada.")


    save_hash_map(new_hashes)
    print("--- Verificação do RAG concluída! ---")


# -----------------------------------------------------------
# Busca vetorial (sem mudanças)
# -----------------------------------------------------------
def vector_search(collection, query: str, alt_query: str, k: int = 20):
    def _safe_query(q):
        try:
            return collection.query(
                query_texts=[q],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
        except Exception as e:
            logger.error(f"Erro na busca vetorial com '{q}': {e}")
            return {"documents": [], "metadatas": [], "distances": [], "ids": []}

    return _safe_query(query), _safe_query(alt_query)