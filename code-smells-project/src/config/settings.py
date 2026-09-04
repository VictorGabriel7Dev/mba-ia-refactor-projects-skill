"""Configuração da aplicação. Nenhum valor sensível literal.

Os defaults são de DESENVOLVIMENTO. O `SECRET_KEY` anterior
("minha-chave-super-secreta-123") não foi mantido como default de propósito: ele
já vazou junto com o repositório, e reaproveitá-lo seria trocar o lugar do
problema. Em produção, defina as variáveis de ambiente.
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bool(nome: str, padrao: bool = False) -> bool:
    return os.environ.get(nome, str(padrao)).strip().lower() in ("1", "true", "yes", "on")


SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DEBUG = _bool("DEBUG", False)
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))

# Caminho do banco relativo à raiz do projeto, e não ao diretório de trabalho:
# `python src/app.py` e `python -m src.app` precisam abrir o mesmo arquivo.
DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(BASE_DIR), "loja.db"))

# Origens permitidas. `*` só se declarado explicitamente no ambiente.
CORS_ORIGENS = [o for o in os.environ.get("CORS_ORIGENS", "http://localhost:3000").split(",") if o]
