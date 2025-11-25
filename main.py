"""
Ponto de entrada da aplicação Flask.
"""

import os
import logging


from app import create_app
from app.chroma_manager import update_embeddings


logger = logging.getLogger("main")
logger.setLevel(logging.INFO)


if __name__ == "__main__":

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    os.chdir(BASE_DIR)

    try:
        update_embeddings()
    except Exception as e:
        print(f"[ERRO GRAVE] Falha ao atualizar embeddings: {e}\n")
        print(">> O servidor será iniciado, mas o RAG pode não funcionar.\n")

    print("\n--- Iniciando servidor Flask ---")

    app_flask = create_app()

    app_flask.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )