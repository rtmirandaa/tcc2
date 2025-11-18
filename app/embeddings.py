# app/embeddings.py (VERSÃO FINAL - Sem Lote, corrigido com 'prompt')

import time
import logging
import ollama
from typing import List, Any

from chromadb.utils.embedding_functions import EmbeddingFunction
from app.config import (
    OLLAMA_EMBEDDING_MODEL,
    EMBEDDING_RETRY_ATTEMPTS,
    EMBEDDING_RETRY_BACKOFF
)

logger = logging.getLogger("app.embeddings")
logger.setLevel(logging.INFO)


class OllamaEmbeddingFunction(EmbeddingFunction):

    # 1. Lógica do __call__ REVERTIDA para "um por um"
    def __call__(self, texts: List[Any]):
        embeddings = []

        # Faz um loop e chama a API para CADA chunk
        for idx, text in enumerate(texts):
            if not isinstance(text, str):
                text = str(text)
            text = text.strip()

            if not text:
                # Se o chunk estiver vazio, adiciona vetor zerado
                embeddings.append([0.0] * 768) # (Ajuste 768 se seu modelo for outro)
                continue

            # Chama a função singular (que usa 'prompt')
            embedding = self._embed_with_retry(text, idx)
            embeddings.append(embedding)

        return embeddings

    
    # 2. Função de retry singular (A QUE SERÁ USADA)
    #    Já estava corrigida para 'prompt'
    def _embed_with_retry(self, text: str, index: int):
        last_error = None
        dimension = 768 # Default

        for attempt in range(EMBEDDING_RETRY_ATTEMPTS):
            try:
                resp = ollama.embeddings(
                    model=OLLAMA_EMBEDDING_MODEL,
                    prompt=text # <--- CORRETO: singular e com 'prompt'
                )

                if isinstance(resp, dict) and "embedding" in resp:
                    emb = resp["embedding"]
                    dimension = len(emb) # Pega a dimensão real
                    return emb

                if hasattr(resp, "embedding"):
                    emb = resp.embedding
                    dimension = len(emb)
                    return emb

                raise ValueError(f"Formato inesperado do Ollama: {resp}")

            except Exception as e:
                last_error = e
                wait = EMBEDDING_RETRY_BACKOFF ** attempt
                logger.warning(
                    f"[Embedding] Falha ao gerar embedding (chunk {index}, tentativa {attempt+1}/"
                    f"{EMBEDDING_RETRY_ATTEMPTS}). Aguardando {wait:.1f}s..."
                )
                time.sleep(wait)

        logger.error(f"[Embedding] ERRO FINAL no chunk {index}: {last_error}")
        
        # Tenta descobrir a dimensão correta mesmo em falha
        try:
            info = ollama.show(OLLAMA_EMBEDDING_MODEL)
            if "parameters" in info:
                for line in info["parameters"].split('\n'):
                    if "embedding_dimensions" in line:
                        dimension = int(line.split()[-1])
                        break
        except Exception:
            pass 
            
        return [0.0] * dimension


    # 3. (Função de batch não é mais chamada, mas pode deixar aqui)
    def _embed_batch_with_retry(self, texts_batch: List[str]):
        logger.warning("[Embedding] _embed_batch_with_retry não é suportada por esta versão do 'ollama'. Revertendo para singular.")
        # Apenas um fallback para não quebrar, caso seja chamada
        return [[0.0] * 768 for _ in range(len(texts_batch))]


def get_embedding_function():
    return OllamaEmbeddingFunction()