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

    def __call__(self, texts: List[Any]):
        embeddings = []

        for idx, text in enumerate(texts):
            if not isinstance(text, str):
                text = str(text)
            text = text.strip()

            if not text:
                embeddings.append([0.0] * 768) 
                continue

            embedding = self._embed_with_retry(text, idx)
            embeddings.append(embedding)

        return embeddings

 
    def _embed_with_retry(self, text: str, index: int):
        last_error = None
        dimension = 768 

        for attempt in range(EMBEDDING_RETRY_ATTEMPTS):
            try:
                resp = ollama.embeddings(
                    model=OLLAMA_EMBEDDING_MODEL,
                    prompt=text 
                )

                if isinstance(resp, dict) and "embedding" in resp:
                    emb = resp["embedding"]
                    dimension = len(emb) 
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


    def _embed_batch_with_retry(self, texts_batch: List[str]):
        logger.warning("[Embedding] _embed_batch_with_retry não é suportada por esta versão do 'ollama'. Revertendo para singular.")
        return [[0.0] * 768 for _ in range(len(texts_batch))]


def get_embedding_function():
    return OllamaEmbeddingFunction()