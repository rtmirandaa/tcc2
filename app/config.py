# app/config.py

import os

# Modelos usados pelo Ollama
OLLAMA_EMBEDDING_MODEL = os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest")
OLLAMA_CHAT_MODEL = os.environ.get("OLLAMA_CHAT_MODEL", "mistral")

# Banco vetorial local
CHROMA_DB_PATH = os.environ.get("CHROMA_DB_PATH", "banco_de_dados_da_ia_local")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "meu_conhecimento")

# Documentos usados no RAG
PDF_FILES = [
    "copia final.pdf"
]

# Tamanhos dos chunks
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 2000))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 300))

# Hash map dos PDFs
HASH_MAP_FILE = "pdf_hashes.json"

# Número máximo de trechos enviados ao modelo
MAX_CONTEXT_CHUNKS = int(os.environ.get("MAX_CONTEXT_CHUNKS", 10))

# Tentativas e backoff dos embeddings
EMBEDDING_RETRY_ATTEMPTS = 3
EMBEDDING_RETRY_BACKOFF = 1.2  # multiplicador de espera

# Termos pedagógicos que recebem boost na busca
PEDAGOGICAL_TERMS = [
    "ppc", "projeto pedagógico", "projeto pedagógico curricular",
    "currículo", "repositório digital", "link oficial", "curso de letras",
    "grade curricular", "prograd", "comgrad", "tcc", "calendário acadêmico"
]
