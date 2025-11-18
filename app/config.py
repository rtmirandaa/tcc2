# app/config.py

import os
import unicodedata


# ============================================================
# NORMALIZAÇÃO DE TERMOS
# ============================================================

def _normalize_term(term: str) -> str:
    """Remove acentos, normaliza e converte para minúsculas."""
    if not isinstance(term, str):
        term = str(term)

    return "".join(
        c for c in unicodedata.normalize("NFD", term)
        if unicodedata.category(c) != "Mn"
    ).lower().strip()


# ============================================================
# MODELOS DO OLLAMA
# ============================================================

OLLAMA_EMBEDDING_MODEL = os.environ.get(
    "OLLAMA_EMBEDDING_MODEL",
    "nomic-embed-text:latest"
)

OLLAMA_CHAT_MODEL = os.environ.get(
    "OLLAMA_CHAT_MODEL",
    "mistral"
)


# ============================================================
# BANCO VETORIAL / CHROMA
# ============================================================

# Caminho ABSOLUTO para garantir que o banco seja persistente
CHROMA_DB_PATH = os.path.abspath(
    os.environ.get(
        "CHROMA_DB_PATH",
        "banco_de_dados_da_ia_local"
    )
)

COLLECTION_NAME = os.environ.get(
    "COLLECTION_NAME",
    "meu_conhecimento"
)


# ============================================================
# DOCUMENTOS DO RAG
# ============================================================

# Seu PDF está na raiz do projeto → caminho relativo OK
PDF_FILES = [
    r"C:\RAG_data\documento_final.pdf"
]
# ============================================================
# CHUNK CONFIG
# ============================================================

CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 2000))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 20))


# ============================================================
# HASH MAP
# ============================================================

HASH_MAP_FILE = "pdf_hashes.json"


# ============================================================
# LIMITES DO CONTEXTO
# ============================================================

MAX_CONTEXT_CHUNKS = int(os.environ.get("MAX_CONTEXT_CHUNKS", 10))


# ============================================================
# RETRY DE EMBEDDINGS
# ============================================================

EMBEDDING_RETRY_ATTEMPTS = 3
EMBEDDING_RETRY_BACKOFF = 1.2


# ============================================================
# TERMOS PEDAGÓGICOS (NORMALIZADOS)
# ============================================================

_RAW_PEDAGOGICAL_TERMS = [
    "ppc",
    "projeto pedagógico",
    "projeto pedagógico curricular",
    "currículo",
    "repositório digital",
    "link oficial",
    "curso de letras",
    "grade curricular",
    "prograd",
    "comgrad",
    "tcc",
    "calendário acadêmico"
]

PEDAGOGICAL_TERMS = [_normalize_term(t) for t in _RAW_PEDAGOGICAL_TERMS]
