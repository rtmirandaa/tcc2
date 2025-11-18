# app/rag_engine.py (COM SAUDAÇÕES E WHATSAPP)

import re
import unicodedata
import logging
import ollama

from app import chroma_manager
from app.config import (
    OLLAMA_CHAT_MODEL,
    MAX_CONTEXT_CHUNKS,
    PEDAGOGICAL_TERMS # (Sem acento, como corrigimos antes)
)
from app.utils import URL_REGEX

logger = logging.getLogger("app.rag_engine")
logger.setLevel(logging.INFO)

# ============================================================
# MENSAGENS PADRÃO
# ============================================================

# Link direto para o WhatsApp da COMGRAD (formato universal)
WHATSAPP_LINK = "https://wa.me/555133086794"

FALLBACK_MSG = (
    "Não encontrei essa informação no Manual do Aluno. "
    "Para casos específicos, entre em contato com a COMGRAD pelo WhatsApp: "
    f"{WHATSAPP_LINK}"
)

GREETINGS_KEYWORDS = {
    "oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", 
    "tudo bem", "e ai", "hey", "opa"
}

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalize_text(s: str) -> str:
    if not s:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    ).lower()

def check_greeting(text_norm: str) -> str:
    """
    Verifica se a pergunta é apenas uma saudação simples.
    """
    # Remove pontuação básica para checar
    clean_text = re.sub(r'[^\w\s]', '', text_norm).strip()
    
    if clean_text in GREETINGS_KEYWORDS:
        return (
            "Olá! Sou o assistente virtual do Instituto de Letras. "
            "Posso tirar suas dúvidas sobre matrículas, TCC, estágios e mais. "
            "Como posso ajudar?"
        )
    return None

def score_chunk(doc_text: str, metadata: dict, q_norm: str):
    score = 1.0
    text_norm = normalize_text(doc_text)

    if metadata.get("contains_paren_link"):
        score *= 3.0
    if any(term in text_norm for term in PEDAGOGICAL_TERMS):
        score *= 1.8
    for word in q_norm.split():
        if len(word) > 2 and word in text_norm:
            score *= 1.4

    return score

def build_context_text(sorted_chunks):
    allowed_urls = set()
    parts = []

    for item in sorted_chunks:
        doc = item["document"]
        md = item["metadata"]

        raw_urls = md.get("source_urls", "")
        urls = raw_urls.split("||") if raw_urls else []
        urls = [u for u in urls if u] 

        for u in urls:
            allowed_urls.add(u)

        label = f"[{md.get('pdf_name')} — página {md.get('page_number')}]"
        block = f"{label}\n{doc}"
        if urls:
            block += "\nLinks encontrados: " + ", ".join(urls)

        parts.append(block)

    context = "\n\n---\n\n".join(parts)
    return context, allowed_urls


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def get_answer_from_rag(query: str) -> str:
    """Processa a pergunta usando busca vetorial + modelo Ollama."""

    if not query or not query.strip():
        return FALLBACK_MSG

    q = query.strip()
    q_norm = normalize_text(q)

    # 1) Checagem rápida de saudação (economiza tempo e recurso)
    greeting_resp = check_greeting(q_norm)
    if greeting_resp:
        return greeting_resp

    # 2) Buscar no vetorstore
    collection = chroma_manager.get_or_create_collection()

    alt_query = (
        f"{q} PPC Projeto Pedagógico Curricular currículo link oficial repositório Letras UFRGS"
    )

    res_main, res_alt = chroma_manager.vector_search(
        collection, q, alt_query, k=25
    )

    docs = []
    for res in (res_main, res_alt):
        if not isinstance(res, dict):
            continue

        _docs = res.get("documents", [])
        _metas = res.get("metadatas", [])
        _ids = res.get("ids", [])

        if _docs and isinstance(_docs[0], list):
            _docs = _docs[0]
        if _metas and isinstance(_metas[0], list):
            _metas = _metas[0]
        if _ids and isinstance(_ids[0], list):
            _ids = _ids[0]

        for doc, md, id_ in zip(_docs, _metas, _ids):
            docs.append({"id": id_, "document": doc, "metadata": md})

    # Se não achou NADA no banco, manda pro WhatsApp
    if not docs:
        return FALLBACK_MSG

    # 3) Ranking
    ranked = []
    for d in docs:
        score = score_chunk(d["document"], d["metadata"], q_norm)
        ranked.append({**d, "score": score})

    ranked.sort(key=lambda x: x["score"], reverse=True)
    top_chunks = ranked[:MAX_CONTEXT_CHUNKS]

    # 4) Montar contexto
    context, allowed_urls = build_context_text(top_chunks)

    # 5) Prompt
    # Instruímos o modelo a usar uma tag específica "SEM_RESPOSTA"
    # para podermos interceptar e colocar o link do Zap.
    system_prompt = (
        "Você é um assistente RAG especializado no Manual do Aluno e documentos oficiais de Letras da UFRGS.\n"
        "Regras:\n"
        "- Use APENAS o conteúdo fornecido no CONTEXT.\n"
        "- Se a resposta não estiver no contexto, responda APENAS: SEM_RESPOSTA\n"
        "- Priorize links que aparecem no contexto.\n"
        "- Não invente links.\n"
        "- Responda com clareza, objetividade e gentileza.\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nPergunta: {q}"}
    ]

    # 6) Chamada ao Ollama
    try:
        resp = ollama.chat(model=OLLAMA_CHAT_MODEL, messages=messages)
        content = ""

        # Parsing robusto (o mesmo que já funcionou)
        if isinstance(resp, dict):
            if "message" in resp and "content" in resp["message"]:
                content = resp["message"]["content"]
            elif "choices" in resp and resp["choices"]:
                content = resp["choices"][0].get("message", {}).get("content", "")
            else:
                logger.warning(f"Formato inesperado: {resp}")
                content = str(resp)
        elif hasattr(resp, 'message') and hasattr(resp.message, 'content'):
            content = resp.message.content
        else:
            logger.warning(f"Formato desconhecido: {resp}")
            content = str(resp)

    except Exception as e:
        logger.exception("Erro ao chamar o Ollama:")
        return FALLBACK_MSG

    # 7) Checagem de Fallback (Intercepta o "SEM_RESPOSTA")
    if "SEM_RESPOSTA" in content or not content.strip():
        return FALLBACK_MSG

    # 8) Limpeza de URLs não permitidas
    detected_urls = set(URL_REGEX.findall(content))
    for url in detected_urls:
        if url not in allowed_urls:
            content = content.replace(url, "[link não disponível no contexto]")

    return content