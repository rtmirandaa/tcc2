# app/rag_engine.py
"""
RAG engine com filtro leve:
 - NUNCA descarta chunks (só prioriza)
 - links entre parênteses têm super prioridade
 - termos pedagógicos têm prioridade
 - busca expandida ajuda muito
 - acentos normalizados para matching de idioma
"""

import re
import logging
import unicodedata
import ollama

from app.config import (
    OLLAMA_CHAT_MODEL,
    MAX_CONTEXT_CHUNKS,
    PEDAGOGICAL_TERMS
)
from app import chroma_manager
from app.utils import URL_REGEX


logger = logging.getLogger("app.rag_engine")
logger.setLevel(logging.INFO)


# ------------------------------------------------------------
# Normalizar para comparação (retira acentos)
# ------------------------------------------------------------
def normalize_text(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    ).lower()


# ------------------------------------------------------------
# Sistema de priorização (SEM DESCARTAR)
# ------------------------------------------------------------
def score_chunk(doc_text: str, metadata: dict, q_norm: str):

    score = 1.0  # base

    text_norm = normalize_text(doc_text)

    # 1) Se tiver link entre parênteses → super boost
    if metadata.get("contains_paren_link"):
        score *= 3.0

    # 2) Se contiver termos pedagógicos
    if any(term in text_norm for term in PEDAGOGICAL_TERMS):
        score *= 1.8

    # 3) Se contém a palavra-chave (normalizada)
    for part in q_norm.split():
        if part and part in text_norm:
            score *= 1.4

    return score


# ------------------------------------------------------------
# Monta contexto final
# ------------------------------------------------------------
def build_context_text(sorted_chunks):
    allowed_urls = set()
    parts = []

    for item in sorted_chunks:
        doc = item["document"]
        md = item["metadata"]

        # converter string -> lista
        raw_urls = md.get("source_urls", "")
        urls = raw_urls.split("||") if raw_urls else []

        for u in urls:
            allowed_urls.add(u)

        label = f"[{md.get('pdf_name')} — página {md.get('page_number')}]"

        block = f"{label}\n{doc}"
        if urls:
            block += "\nLinks encontrados: " + ", ".join(urls)

        parts.append(block)

    context = "\n\n---\n\n".join(parts)
    return context, allowed_urls


# ------------------------------------------------------------
# Função principal do RAG
# ------------------------------------------------------------
def get_answer_from_rag(query: str) -> str:

    if not query or not query.strip():
        return "Não tenho informações sobre isso."

    q = query.strip()
    q_norm = normalize_text(q)

    # ------------------------
    # Busca no banco vetorial
    # ------------------------
    collection = chroma_manager.get_or_create_collection()

    alt_query = (
        f"{q} PPC Projeto Pedagógico Curricular link oficial currículo repositório"
    )

    res_main, res_alt = chroma_manager.vector_search(
        collection, q, alt_query, k=25
    )

    # Extrair documentos
    docs = []
    for res in (res_main, res_alt):
        if not res:
            continue

        _docs = res.get("documents", [])
        _metas = res.get("metadatas", [])
        _ids = res.get("ids", [])

        # Flatten se necessário
        if _docs and isinstance(_docs[0], list):
            _docs = _docs[0]
        if _metas and isinstance(_metas[0], list):
            _metas = _metas[0]
        if _ids and isinstance(_ids[0], list):
            _ids = _ids[0]

        for doc, md, id_ in zip(_docs, _metas, _ids):
            docs.append({"id": id_, "document": doc, "metadata": md})

    if not docs:
        return "Não tenho informações sobre isso."

    # ------------------------
    # Priorizar (SEM DESCARTAR)
    # ------------------------
    ranked = []
    for d in docs:
        s = score_chunk(
            d["document"],
            d["metadata"],
            q_norm
        )
        ranked.append({**d, "score": s})

    ranked.sort(key=lambda x: x["score"], reverse=True)

    # Selecionar top chunks
    top_chunks = ranked[:MAX_CONTEXT_CHUNKS]

    # ------------------------
    # Montar contexto
    # ------------------------
    context, allowed_urls = build_context_text(top_chunks)

    # ------------------------
    # Gerar resposta com o Ollama
    # ------------------------
    system_prompt = (
        "Você é um assistente RAG restrito ao PDF do Manual do Aluno e documentos de Letras.\n"
        "Regras:\n"
        "- Use APENAS o conteúdo do CONTEXT.\n"
        "- Priorize links dentro de parênteses.\n"
        "- NÃO invente links.\n"
        "- Se a resposta não estiver no contexto, responda: Não tenho informações sobre isso.\n"
        "- Se houver links, mantenha exatamente como aparecem.\n"
        "- Responda de forma objetiva.\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"CONTEXT:\n{context}\n\nPergunta: {q}"}
    ]

    try:
        resp = ollama.chat(model=OLLAMA_CHAT_MODEL, messages=messages)
        content = resp["message"]["content"]
    except Exception as e:
        print(e)
        return "Erro ao gerar resposta."

    # ------------------------
    # Remover links inventados
    # ------------------------
    detected = set(URL_REGEX.findall(content))

    for u in detected:
        if u not in allowed_urls:
            content = content.replace(u, "[link não disponível no contexto]")

    if not content.strip():
        return "Não tenho informações sobre isso."

    return content
