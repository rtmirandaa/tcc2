import re
import unicodedata

URL_REGEX = re.compile(
    r"(https?://[^\s\)\]\}\>\.,;:]+)"
)

PAREN_LINK_REGEX = re.compile(
    r"\([^()]*https?://[^\s\)]+[^()]*\)"
)


def extract_urls(text: str):
    """
    Extrai todas as URLs de um texto usando regex robusta.
    Retorna lista de strings.
    """
    if not text:
        return []
    return URL_REGEX.findall(text)


def contains_paren_link(text: str) -> bool:
    """
    Detecta se existe link dentro de parênteses.
    Usado no RAG para dar boost de relevância.
    """
    if not text:
        return False
    return bool(PAREN_LINK_REGEX.search(text))

def normalize_whitespace(s: str) -> str:
    """
    Remove múltiplos espaços, tabs e quebras de linha excessivas.
    """
    if not s:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def normalize_text(s: str) -> str:
    """
    Remove acentos, converte para minúsculas e normaliza whitespace.
    Bom para matching e scoring no RAG.
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = normalize_whitespace(s)

    return s

def detect_language_heuristic(text: str) -> str:
    """
    Heurística muito simples para detectar idioma.
    Apenas fallback — não é usada no RAG principal.
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

    return "pt"
