# app/__init__.py

from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    CORS(app)

    # Importa rotas (serão criadas depois)
    from app.routes import register_routes
    register_routes(app)

    return app
