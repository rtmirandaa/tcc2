# app/routes.py
"""
Rotas da aplicação Flask.

Inclui:
- Página inicial ("/")
- Endpoint principal /ask (POST)
- Endpoint /admin/inspect (debug da busca vetorial)
"""

from flask import request, jsonify, render_template
import logging

from app.rag_engine import get_answer_from_rag
from app.chroma_manager import get_or_create_collection, vector_search
from app.config import PEDAGOGICAL_TERMS


logger = logging.getLogger("app.routes")
logger.setLevel(logging.INFO)


# ---------------------------------------------------------
# Utilitário para converter resultados do Chroma em JSON
# ---------------------------------------------------------
def _json_safe(obj):
    import numpy as np

    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [_json_safe(x) for x in obj]

    # numpy → tipos nativos
    if isinstance(obj, (np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, (np.int32, np.int64)):
        return int(obj)

    return obj


# ---------------------------------------------------------
# Registro das rotas
# ---------------------------------------------------------
def register_routes(app):

    # -----------------------------------------------------
    # Página inicial
    # -----------------------------------------------------
    @app.route("/")
    def home():
        return render_template("index.html")

    # -----------------------------------------------------
    # Endpoint principal /ask
    # -----------------------------------------------------
    @app.route("/ask", methods=["POST"])
    def ask_api():
        data = request.get_json(force=True) or {}

        question = data.get("question", "").strip()

        if not question:
            return jsonify({"answer": "Não tenho informações sobre isso."})

        logger.info(f"[Pergunta] {question}")

        answer = get_answer_from_rag(question)

        return jsonify({"answer": answer})

    # -----------------------------------------------------
    # Endpoint de inspeção vetorial (debug)
    # -----------------------------------------------------
    @app.route("/admin/inspect", methods=["GET"])
    def inspect():
        """
        Exemplo:
        /admin/inspect?q=qual+o+email+da+comgrad
        """

        q = request.args.get("q", "").strip()

        if not q:
            return jsonify({"error": "Parâmetro 'q' é obrigatório."}), 400

        logger.info(f"[Inspect] Query: {q}")

        collection = get_or_create_collection()

        alt_terms = " ".join(PEDAGOGICAL_TERMS)
        alt_query = f"{q} {alt_terms}"

        res_main, res_alt = vector_search(collection, q, alt_query)

        return jsonify({
            "query": q,
            "main_results": _json_safe(res_main),
            "alt_results": _json_safe(res_alt)
        })
