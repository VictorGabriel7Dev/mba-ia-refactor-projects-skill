"""Configuração vinda do ambiente. Nenhum segredo literal."""
import os


def _bool(nome: str, padrao: bool = False) -> bool:
    return os.environ.get(nome, str(padrao)).strip().lower() in ("1", "true", "yes", "on")


SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DEBUG = _bool("DEBUG", False)
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))

SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///tasks.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

CORS_ORIGENS = [o for o in os.environ.get("CORS_ORIGENS", "http://localhost:3000").split(",") if o]

# Servidor de e-mail. A senha era 'senha123' literal no serviço de notificação.
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USER = os.environ.get("EMAIL_USER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
