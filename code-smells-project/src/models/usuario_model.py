"""Acesso a dados de usuário.

`PUBLICO` existe para que nenhuma rota consiga devolver a senha por descuido: a
projeção é explícita e a coluna `senha` só sai do banco em `credencial_por_email`,
que é usada apenas pela autenticação.
"""
from database import get_db

PUBLICO = ("id", "nome", "email", "tipo", "criado_em")


def _publico(row):
    return {c: row[c] for c in PUBLICO} if row else None


def listar():
    cur = get_db().execute("SELECT id, nome, email, tipo, criado_em FROM usuarios")
    return [_publico(r) for r in cur.fetchall()]


def por_id(usuario_id: int):
    cur = get_db().execute(
        "SELECT id, nome, email, tipo, criado_em FROM usuarios WHERE id = ?", (usuario_id,))
    return _publico(cur.fetchone())


def credencial_por_email(email: str):
    """Única consulta que traz o hash da senha."""
    cur = get_db().execute(
        "SELECT id, nome, email, tipo, senha FROM usuarios WHERE email = ?", (email,))
    return cur.fetchone()


def criar(nome, email, senha_hash, tipo="cliente") -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        (nome, email, senha_hash, tipo))
    db.commit()
    return cur.lastrowid
