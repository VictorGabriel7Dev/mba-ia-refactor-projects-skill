"""Composition root: monta a aplicação e conecta as camadas. Nenhuma regra aqui."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from flask_cors import CORS

import database
from config import settings
from middlewares import error_handler
from views.routes import bp


def criar_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG

    CORS(app, origins=settings.CORS_ORIGENS)
    database.registrar(app)
    error_handler.registrar(app)
    app.register_blueprint(bp)
    return app


app = criar_app()

if __name__ == "__main__":
    database.inicializar()
    print("=" * 50)
    print("SERVIDOR INICIADO")
    print(f"Rodando em http://{settings.HOST}:{settings.PORT}")
    print("=" * 50)
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
