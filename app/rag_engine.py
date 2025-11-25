# app/rag_engine.py

import re
import unicodedata
import logging
import google.generativeai as genai

from app import chroma_manager
# AQUI IMPORTAMOS A CHAVE DO ARQUIVO DE CONFIGURAÇÃO
from app.config import (
    GEMINI_API_KEY,      
    GEMINI_MODEL_NAME,
    MAX_CONTEXT_CHUNKS,
    PEDAGOGICAL_TERMS
)
from app.utils import URL_REGEX

logger = logging.getLogger("app.rag_engine")
logger.setLevel(logging.INFO)

# ============================================================
# CONFIGURAÇÃO SEGURA
# ============================================================
# Note que aqui usamos a variável importada, não o texto solto
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.error(f"Erro ao configurar API do Gemini: {e}")

# ... (MANTENHA AS MENSAGENS PADRÃO IGUAIS) ...

WHATSAPP_LINK = "https://wa.me/555133086794"

FALLBACK_MSG = (
    "Poxa, não encontrei essa informação específica no Manual do Aluno. "
    "Como meu conhecimento é limitado aos documentos oficiais, "
    "sugiro que você converse diretamente com a COMGRAD pelo WhatsApp para ter certeza: "
    f"{WHATSAPP_LINK}"
)

GREETINGS_KEYWORDS = {
    "oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", 
    "tudo bem", "e ai", "hey", "opa"
}

CONTACT_RESPONSE = (
    "Claro! Aqui estão os contatos oficiais da COMGRAD (Comissão de Graduação de Letras):\n\n"
    "• E-mail: comlet@ufrgs.br\n"
    "• Telefone/WhatsApp: (51) 3308-6794\n"
    "• Localização: Campus do Vale, Porto Alegre.\n"
    "• Site: www.ufrgs.br/letras"
)

# ... (MANTENHA AS FUNÇÕES AUXILIARES IGUAIS: normalize, greeting, contact, score, build) ...

def normalize_text(s: str) -> str:
    if not s: return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn").lower()

def check_greeting(text_norm: str) -> str:
    clean_text = re.sub(r'[^\w\s]', '', text_norm).strip()
    if clean_text in GREETINGS_KEYWORDS:
        return "Olá! Sou o assistente virtual do Instituto de Letras. Estou aqui para te ajudar com dúvidas sobre o curso, matrículas e TCC. O que você precisa?"
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
    
    wants_contact = any(x in q_norm for x in ["contato", "email", "fone", "telefone"])
    has_data = any(x in text_norm for x in ["@", "3308", "(51)", "comlet"])
    if wants_contact and has_data: score *= 10.0

    if "tcc" in q_norm and ("document" in q_norm or "entrega" in q_norm or "obrigatorio" in q_norm):
        tcc_keywords = ["termo de autorizacao", "ata de defesa", "requerimento de matricula", "arquivo do tcc", "biblioteca lume"]
        if any(k in text_norm for k in tcc_keywords): score *= 20.0

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
        if urls: block += "\nLinks úteis: " + ", ".join(urls)
        parts.append(block)
    context = "\n\n---\n\n".join(parts)
    return context, allowed_urls

def get_answer_from_rag(query: str) -> str:
    if not query or not query.strip(): return FALLBACK_MSG

    q = query.strip()
    q_correct = q.replace("congrad", "comgrad").replace("CONGRAD", "COMGRAD")
    q_norm = normalize_text(q_correct)

    if check_greeting(q_norm): return check_greeting(q_norm)
    if check_contact_intent(q_norm): return check_contact_intent(q_norm)

    try:
        collection = chroma_manager.get_or_create_collection()
        alt_query = f"{q_correct} PPC Projeto Pedagógico Curricular currículo link oficial repositório Letras UFRGS"
        res_main, res_alt = chroma_manager.vector_search(collection, q_correct, alt_query, k=10)
    except Exception as e:
        logger.error(f"Erro na busca vetorial: {e}")
        return FALLBACK_MSG

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

    ranked = []
    for d in docs:
        score = score_chunk(d["document"], d["metadata"], q_norm)
        ranked.append({**d, "score": score})
    
    ranked.sort(key=lambda x: x["score"], reverse=True)
    top_chunks = ranked[:MAX_CONTEXT_CHUNKS]
    context, allowed_urls = build_context_text(top_chunks)

    final_prompt = (
        f"Você é o assistente virtual oficial do Instituto de Letras da UFRGS.\n"
        f"Use EXCLUSIVAMENTE o contexto abaixo para responder à dúvida do aluno.\n\n"
        f"CONTEXTO (Manual do Aluno):\n{context}\n\n"
        f"DÚVIDA DO ALUNO: {q}\n\n"
        "--- DIRETRIZES ---\n"
        "1. Seja educado, acolhedor e direto.\n"
        "2. Use apenas as informações fornecidas no contexto. Se a informação não estiver lá, diga: SEM_RESPOSTA\n"
        "3. Responda em português claro.\n"
        "4. Formate a resposta com quebras de linha para facilitar a leitura.\n"
    )

    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        
        generation_config = genai.types.GenerationConfig(
            temperature=0.2,
            top_p=0.8,
            top_k=40
        )

        response = model.generate_content(
            final_prompt,
            generation_config=generation_config
        )
        
        content = response.text

    except Exception as e:
        logger.exception("Erro ao chamar API do Gemini:")
        return FALLBACK_MSG

    if "SEM_RESPOSTA" in content or not content.strip():
        return FALLBACK_MSG

    detected_urls = set(URL_REGEX.findall(content))
    for url in detected_urls:
        if url not in allowed_urls:
            content = content.replace(url, "")

    return content