# app/embeddings.py

import ollama
from chromadb.utils.embedding_functions import EmbeddingFunction
from app.config import OLLAMA_EMBEDDING_MODEL

class OllamaEmbeddingFunction(EmbeddingFunction):
    """
    Função de embeddings COMPATÍVEL com o ChromaDB.
    - Recebe uma LISTA de textos
    - Retorna uma LISTA de embeddings
    - Sem batch (batch falha no Windows)
    """

    def __call__(self, texts):
        embeddings = []

        for idx, text in enumerate(texts):
            if not isinstance(text, str):
                text = str(text)

            resp = ollama.embeddings(model=OLLAMA_EMBEDDING_MODEL, prompt=text)

            if resp is None or "embedding" not in resp:
                raise ValueError(
                    f"[Embedding Error] Falha ao gerar embedding no item {idx}."
                )

            embeddings.append(resp["embedding"])

        return embeddings


def get_embedding_function():
    return OllamaEmbeddingFunction()
