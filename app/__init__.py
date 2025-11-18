# app/__init__.py

import os
import logging
from flask import Flask
from flask_cors import CORS


logger = logging.getLogger("app.__init__")
logger.setLevel(logging.INFO)


def create_app():
    """
    Inicializa a aplicação Flask com CORS e registra rotas.
    Usa caminhos absolutos para garantir compatibilidade.
    """

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "../templates"),
        static_folder=os.path.join(BASE_DIR, "../static")
    )

    CORS(app)

    logger.info("[Flask] Aplicação inicializada.")

    # Registrar rotas
    from app.routes import register_routes
    register_routes(app)

    logger.info("[Flask] Rotas registradas.")

    return app
