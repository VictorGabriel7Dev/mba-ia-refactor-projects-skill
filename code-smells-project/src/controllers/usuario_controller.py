"""Regra de negócio de usuário e autenticação."""
from middlewares.error_handler import ErroDeAplicacao
from models import usuario_model
from security import hash_senha, verificar_senha


def listar():
    return usuario_model.listar()


def obter(usuario_id):
    usuario = usuario_model.por_id(usuario_id)
    if not usuario:
        raise ErroDeAplicacao("Usuário não encontrado", 404)
    return usuario


def criar(dados):
    if not dados:
        raise ErroDeAplicacao("Dados inválidos")
    nome, email, senha = dados.get("nome", ""), dados.get("email", ""), dados.get("senha", "")
    if not nome or not email or not senha:
        raise ErroDeAplicacao("Nome, email e senha são obrigatórios")
    return {"id": usuario_model.criar(nome, email, hash_senha(senha))}


def autenticar(dados):
    if not dados:
        raise ErroDeAplicacao("Dados inválidos")
    email, senha = dados.get("email", ""), dados.get("senha", "")
    if not email or not senha:
        raise ErroDeAplicacao("Email e senha são obrigatórios")

    row = usuario_model.credencial_por_email(email)
    # A verificação roda em Python, e não dentro do SQL. Era a comparação na query
    # que transformava a autenticação no vetor da injeção.
    if not row or not verificar_senha(senha, row["senha"]):
        raise ErroDeAplicacao("Email ou senha inválidos", 401)
    return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}
