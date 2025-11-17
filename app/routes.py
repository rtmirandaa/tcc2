# app/routes.py
"""
Define todas as rotas da aplicação Flask.
Integra frontend, endpoint principal /ask e endpoint de inspeção /admin/inspect.
"""

from flask import request, jsonify, render_template

from app.rag_engine import get_answer_from_rag
from app.chroma_manager import get_or_create_collection, vector_search
from app.config import PEDAGOGICAL_TERMS


def register_routes(app):

    # --------------------------
    # Página inicial
    # --------------------------
    @app.route("/")
    def home():
        return render_template("index.html")

    # --------------------------
    # Endpoint principal /ask
    # --------------------------
    @app.route("/ask", methods=["POST"])
    def ask_api():
        data = request.get_json(force=True)
        question = data.get("question", "").strip()

        if not question:
            return jsonify({"answer": "Não tenho informações sobre isso."})

        answer = get_answer_from_rag(question)
        return jsonify({"answer": answer})

    # --------------------------
    # Endpoint de inspeção — para debug
    # --------------------------
    @app.route("/admin/inspect", methods=["GET"])
    def inspect():
        q = request.args.get("q", "").strip()
        if not q:
            return jsonify({"error": "Parâmetro 'q' é obrigatório."}), 400

        # Carrega coleção
        collection = get_or_create_collection()

        # Cria alt_query
        alt_terms = " ".join(PEDAGOGICAL_TERMS)
        alt_query = f"{q} {alt_terms}"

        # Faz buscas
        res_main, res_alt = vector_search(collection, q, alt_query)

        return jsonify({
            "query": q,
            "main_results": res_main,
            "alt_results": res_alt
        })
