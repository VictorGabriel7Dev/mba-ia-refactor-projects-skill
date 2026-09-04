"""Acesso a dados de produto. Só SQL parametrizado, sem regra de negócio."""
from database import get_db

CAMPOS = ("id", "nome", "descricao", "preco", "estoque", "categoria", "ativo", "criado_em")


def _linha(row):
    return {c: row[c] for c in CAMPOS} if row else None


def listar():
    cur = get_db().execute("SELECT * FROM produtos")
    return [_linha(r) for r in cur.fetchall()]


def por_id(produto_id: int):
    cur = get_db().execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
    return _linha(cur.fetchone())


def criar(nome, descricao, preco, estoque, categoria) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria)"
        " VALUES (?, ?, ?, ?, ?)", (nome, descricao, preco, estoque, categoria))
    db.commit()
    return cur.lastrowid


def atualizar(produto_id, nome, descricao, preco, estoque, categoria) -> None:
    db = get_db()
    db.execute(
        "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?,"
        " categoria = ? WHERE id = ?",
        (nome, descricao, preco, estoque, categoria, produto_id))
    db.commit()


def deletar(produto_id: int) -> None:
    db = get_db()
    db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    db.commit()


def buscar(termo=None, categoria=None, preco_min=None, preco_max=None):
    """Filtro montado dinamicamente, mas SEMPRE com placeholder."""
    sql, params = "SELECT * FROM produtos WHERE 1=1", []
    if termo:
        sql += " AND (nome LIKE ? OR descricao LIKE ?)"
        params += [f"%{termo}%", f"%{termo}%"]
    if categoria:
        sql += " AND categoria = ?"
        params.append(categoria)
    if preco_min is not None:
        sql += " AND preco >= ?"
        params.append(preco_min)
    if preco_max is not None:
        sql += " AND preco <= ?"
        params.append(preco_max)
    return [_linha(r) for r in get_db().execute(sql, params).fetchall()]
