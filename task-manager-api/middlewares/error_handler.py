"""Tratamento de erro centralizado.

Antes havia `except:` nu em vários handlers, que engolia qualquer exceção e
devolvia 'Erro interno' sem registrar nada. Agora o detalhe vai para o log e o
cliente recebe sempre o mesmo formato, `{"error": ...}`, que é o que a API já
usava nas respostas de erro.
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException


class ErroDeAplicacao(Exception):
    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def registrar(app) -> None:
    @app.errorhandler(ErroDeAplicacao)
    def _erro_aplicacao(e: ErroDeAplicacao):
        return jsonify({"error": e.mensagem}), e.status

    @app.errorhandler(HTTPException)
    def _erro_http(e: HTTPException):
        return jsonify({"error": e.description}), e.code

    @app.errorhandler(Exception)
    def _inesperado(e: Exception):
        app.logger.exception("erro nao tratado", exc_info=e)
        return jsonify({"error": "Erro interno"}), 500
