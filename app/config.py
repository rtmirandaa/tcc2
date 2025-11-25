import os
import unicodedata

def _normalize_term(term: str) -> str:
    if not isinstance(term, str):
        term = str(term)
    return "".join(
        c for c in unicodedata.normalize("NFD", term)
        if unicodedata.category(c) != "Mn"
    ).lower().strip()


GEMINI_API_KEY = "" 

GEMINI_MODEL_NAME = "gemini-2.0-flash"

OLLAMA_EMBEDDING_MODEL = "nomic-embed-text:latest"



CHROMA_DB_PATH = os.path.abspath(os.environ.get("CHROMA_DB_PATH", "banco_de_dados_da_ia_local"))
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "meu_conhecimento")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(APP_DIR)
PDF_FILES = [os.path.join(PROJECT_ROOT, "arquivos", "documento_final.pdf")]

CHUNK_SIZE = 1000 
CHUNK_OVERLAP = 100
HASH_MAP_FILE = "pdf_hashes.json"

MAX_CONTEXT_CHUNKS = 5

EMBEDDING_RETRY_ATTEMPTS = 3
EMBEDDING_RETRY_BACKOFF = 1.2

_RAW_PEDAGOGICAL_TERMS = [
    "ppc", "projeto pedagógico", "currículo", "repositório digital",
    "link oficial", "curso de letras", "grade curricular", "prograd",
    "comgrad", "tcc", "calendário acadêmico", "estágio", "matrícula"
]

PEDAGOGICAL_TERMS = [_normalize_term(t) for t in _RAW_PEDAGOGICAL_TERMS]