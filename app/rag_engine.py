# app/rag_engine.py

import re
import unicodedata
import logging
import ollama

from app import chroma_manager
from app.config import (
    OLLAMA_CHAT_MODEL,
    MAX_CONTEXT_CHUNKS,
    PEDAGOGICAL_TERMS
)
from app.utils import URL_REGEX

logger = logging.getLogger("app.rag_engine")
logger.setLevel(logging.INFO)

# ============================================================
# MENSAGENS PADRÃO
# ============================================================

WHATSAPP_LINK = "https://wa.me/555133086794"

FALLBACK_MSG = (
    "Não encontrei essa informação detalhada no Manual do Aluno. "
    "Pode ser algo muito específico. "
    "Recomendo confirmar com a COMGRAD pelo WhatsApp: "
    f"{WHATSAPP_LINK}"
)

GREETINGS_KEYWORDS = {
    "oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", 
    "tudo bem", "e ai", "hey", "opa"
}

# Resposta estática para contatos (Essa não falha)
CONTACT_RESPONSE = (
    "Aqui estão os contatos oficiais da COMGRAD (Comissão de Graduação de Letras):\n\n"
    "• E-mail: comlet@ufrgs.br\n"
    "• Telefone/WhatsApp: (51) 3308-6794\n"
    "• Localização: Campus do Vale, Porto Alegre.\n"
    "• Site: www.ufrgs.br/letras"
)

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalize_text(s: str) -> str:
    if not s: return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()

def check_greeting(text_norm: str) -> str:
    clean_text = re.sub(r'[^\w\s]', '', text_norm).strip()
    if clean_text in GREETINGS_KEYWORDS:
        return "Olá! Sou o assistente virtual do Instituto de Letras. Posso tirar suas dúvidas sobre o Manual do Aluno. Como posso ajudar?"
    return None

def check_contact_intent(text_norm: str) -> str:
    triggers = ["contato", "email", "e-mail", "fone", "telefone", "whatsapp", "onde fica", "falar com", "ligar"]
    target = ["comgrad", "congrad", "secretaria", "coordenação", "letras", "curso"]
    if any(t in text_norm for t in triggers) and any(tg in text_norm for tg in target):
        return CONTACT_RESPONSE
    return None

def score_chunk(doc_text: str, metadata: dict, q_norm: str):
    score = 1.0
    text_norm = normalize_text(doc_text)
    if metadata.get("contains_paren_link"): score *= 3.0
    if any(term in text_norm for term in PEDAGOGICAL_TERMS): score *= 1.8
    for word in q_norm.split():
        if len(word) > 2 and word in text_norm: score *= 1.4
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
        for u in urls: allowed_urls.add(u)
        
        block = f"{doc}"
        if urls: block += "\nLinks: " + ", ".join(urls)
        parts.append(block)
    
    context = "\n\n---\n\n".join(parts)
    return context, allowed_urls

# ============================================================
# PIPELINE PRINCIPAL
# ============================================================

def get_answer_from_rag(query: str) -> str:
    if not query or not query.strip(): return FALLBACK_MSG

    q = query.strip()
    q_correct = q.replace("congrad", "comgrad").replace("CONGRAD", "COMGRAD")
    q_norm = normalize_text(q_correct)

    # 1) Saudação
    greeting_resp = check_greeting(q_norm)
    if greeting_resp: return greeting_resp

    # 2) Contato (Curto-Circuito)
    contact_resp = check_contact_intent(q_norm)
    if contact_resp: return contact_resp

    # 3) Busca
    collection = chroma_manager.get_or_create_collection()
    alt_query = f"{q_correct} PPC Projeto Pedagógico Curricular currículo link oficial repositório Letras UFRGS"
    res_main, res_alt = chroma_manager.vector_search(collection, q_correct, alt_query, k=25)

    docs = []
    for res in (res_main, res_alt):
        if not isinstance(res, dict): continue
        _docs = res.get("documents", [])
        _metas = res.get("metadatas", [])
        _ids = res.get("ids", [])
        
        if _docs and isinstance(_docs[0], list): _docs = _docs[0]
        if _metas and isinstance(_metas[0], list): _metas = _metas[0]
        if _ids and isinstance(_ids[0], list): _ids = _ids[0]

        for doc, md, id_ in zip(_docs, _metas, _ids):
            docs.append({"id": id_, "document": doc, "metadata": md})

    if not docs: return FALLBACK_MSG

    # 4) Ranking
    ranked = []
    for d in docs:
        score = score_chunk(d["document"], d["metadata"], q_norm)
        ranked.append({**d, "score": score})
    
    ranked.sort(key=lambda x: x["score"], reverse=True)
    top_chunks = ranked[:MAX_CONTEXT_CHUNKS]
    context, allowed_urls = build_context_text(top_chunks)

    # 5) Prompt (EQUILIBRADO)
    # Liberamos ele para responder, mas mantemos o bloqueio de assuntos aleatórios.
    final_prompt = (
        f"CONTEXTO DO MANUAL ACADÊMICO:\n{context}\n\n"
        f"PERGUNTA DO ALUNO: {q}\n\n"
        "--- INSTRUÇÕES ---\n"
        "1. Você é um assistente do Instituto de Letras. Responda à pergunta usando as informações do CONTEXTO acima.\n"
        "2. Se a informação estiver no texto, explique-a de forma útil para o aluno.\n"
        "3. BLOQUEIO DE ASSUNTO: Se a pergunta for sobre conhecimentos gerais (Geografia, História, Ciência, Capitais) que NÃO têm relação com o curso ou a UFRGS, responda APENAS: SEM_RESPOSTA\n"
        "4. Se o contexto não tiver NENHUMA informação sobre o tema perguntado, responda: SEM_RESPOSTA\n"
        "5. Responda em português.\n"
    )

    messages = [
        {"role": "user", "content": final_prompt}
    ]

    # 6) Chamada ao Ollama
    try:
        resp = ollama.chat(
            model=OLLAMA_CHAT_MODEL, 
            messages=messages,
            options={'temperature': 0} 
        )
        
        content = ""
        if isinstance(resp, dict):
            if "message" in resp and "content" in resp["message"]: content = resp["message"]["content"]
            elif "choices" in resp and resp["choices"]: content = resp["choices"][0].get("message", {}).get("content", "")
            else: content = str(resp)
        elif hasattr(resp, 'message') and hasattr(resp.message, 'content'):
            content = resp.message.content
        else:
            content = str(resp)
    except Exception as e:
        logger.exception("Erro ao chamar o Ollama:")
        return FALLBACK_MSG

    # 7) Fallback (Removemos a lista de frases proibidas, confiamos no SEM_RESPOSTA)
    if "SEM_RESPOSTA" in content or not content.strip():
        return FALLBACK_MSG

    # 8) Limpeza
    detected_urls = set(URL_REGEX.findall(content))
    for url in detected_urls:
        if url not in allowed_urls:
            content = content.replace(url, "")

    return content