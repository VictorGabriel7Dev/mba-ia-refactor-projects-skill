"""Tratamento de erro centralizado.

Antes cada handler repetia `except Exception as e: return jsonify({"erro": str(e)}), 500`,
o que devolvia a mensagem interna ao cliente e não dava formato único. Agora o
detalhe vai para o log e o cliente recebe sempre a mesma forma.
"""
from flask import jsonify
from werkzeug.exceptions import HTTPException


class ErroDeAplicacao(Exception):
    """Erro esperado, com status HTTP próprio."""

    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def registrar(app) -> None:
    @app.errorhandler(ErroDeAplicacao)
    def _erro_aplicacao(e: ErroDeAplicacao):
        return jsonify({"erro": e.mensagem, "sucesso": False}), e.status

    @app.errorhandler(HTTPException)
    def _erro_http(e: HTTPException):
        return jsonify({"erro": e.description, "sucesso": False}), e.code

    @app.errorhandler(Exception)
    def _inesperado(e: Exception):
        app.logger.exception("erro nao tratado", exc_info=e)
        return jsonify({"erro": "Erro interno", "sucesso": False}), 500
