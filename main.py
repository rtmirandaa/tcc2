# main.py
"""
Ponto de entrada da aplicação.
Inicia o Flask carregando a estrutura modular (app/__init__.py).
Também garante atualização dos embeddings antes de iniciar o servidor.
"""

from app import create_app
from app.chroma_manager import update_embeddings


if __name__ == "__main__":
    # Atualiza embeddings dos PDFs antes de subir o servidor
    print("[INFO] Atualizando embeddings dos PDFs...")
    update_embeddings()

    print("[INFO] Iniciando servidor Flask...")
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
