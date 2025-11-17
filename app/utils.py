# app/utils.py

import re
import unicodedata

# ==============================
# REGEX E DETECÇÃO DE LINKS
# ==============================

# Captura URLs comuns (http/https)
URL_REGEX = re.compile(r"(https?://[^\s\)\]]+)")

# Captura links dentro de parênteses (prioritários para o RAG)
PAREN_LINK_REGEX = re.compile(r"\([^)]*https?://[^\s)]+\)")


def extract_urls(text: str):
    """
    Extrai todas as URLs presentes em um texto.
    """
    if not text:
        return []
    return URL_REGEX.findall(text)


def contains_paren_link(text: str) -> bool:
    """
    Determina se o texto contém links oficiais dentro de parênteses.
    Esses trechos recebem prioridade na busca.
    """
    if not text:
        return False
    return bool(PAREN_LINK_REGEX.search(text))


# ==============================
# NORMALIZAÇÕES
# ==============================

def normalize_whitespace(s: str) -> str:
    """
    Remove múltiplos espaços, quebras de linha excessivas
    e normaliza o texto para leitura.
    """
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def normalize_text(s: str) -> str:
    """
    Remove acentuação, converte para minúsculas e normaliza espaços.
    Pode ser útil para matching de textos.
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = normalize_whitespace(s)
    return s


# ==============================
# DETECÇÃO DE IDIOMA (HEURÍSTICA)
# ==============================

def detect_language_heuristic(text: str) -> str:
    """
    Detecção simples de idioma baseada em palavras-chave.
    Usada como fallback quando langdetect não estiver disponível.
    """
    if not text:
        return "pt"

    t = text.lower()

    if any(w in t for w in ["alemão", "alemao", "german", "deutsch"]):
        return "de"
    if any(w in t for w in ["inglês", "ingles", "english"]):
        return "en"
    if any(w in t for w in ["francês", "frances", "français", "francais"]):
        return "fr"
    if any(w in t for w in ["espanhol", "espanol", "español"]):
        return "es"
    if any(w in t for w in ["italiano", "italian", "italien"]):
        return "it"

    return "pt"  # fallback padrão
