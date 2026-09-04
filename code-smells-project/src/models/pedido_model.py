"""Acesso a dados de pedido.

A listagem antes disparava 1 + N + N*M consultas (itens por pedido, produto por
item). Aqui são DUAS: uma para os pedidos e uma para todos os itens, com JOIN em
produtos, agrupada em memória.
"""
from database import get_db

_SQL_ITENS = """
    SELECT ip.pedido_id, ip.produto_id, ip.quantidade, ip.preco_unitario,
           p.nome AS produto_nome
      FROM itens_pedido ip
      LEFT JOIN produtos p ON p.id = ip.produto_id
     WHERE ip.pedido_id IN ({})
"""


def _montar(rows):
    pedidos = [{"id": r["id"], "usuario_id": r["usuario_id"], "status": r["status"],
                "total": r["total"], "criado_em": r["criado_em"], "itens": []}
               for r in rows]
    if not pedidos:
        return pedidos
    ids = [p["id"] for p in pedidos]
    marcadores = ",".join("?" for _ in ids)
    itens = get_db().execute(_SQL_ITENS.format(marcadores), ids).fetchall()
    por_pedido = {p["id"]: p for p in pedidos}
    for it in itens:
        por_pedido[it["pedido_id"]]["itens"].append({
            "produto_id": it["produto_id"],
            "produto_nome": it["produto_nome"] or "Desconhecido",
            "quantidade": it["quantidade"],
            "preco_unitario": it["preco_unitario"],
        })
    return pedidos


def listar():
    return _montar(get_db().execute("SELECT * FROM pedidos").fetchall())


def por_usuario(usuario_id: int):
    return _montar(get_db().execute(
        "SELECT * FROM pedidos WHERE usuario_id = ?", (usuario_id,)).fetchall())


def produtos_por_ids(ids):
    if not ids:
        return {}
    marcadores = ",".join("?" for _ in ids)
    rows = get_db().execute(
        f"SELECT id, nome, preco, estoque FROM produtos WHERE id IN ({marcadores})",
        list(ids)).fetchall()
    return {r["id"]: dict(r) for r in rows}


def registrar(usuario_id, total, itens):
    """Grava pedido, itens e baixa de estoque numa transação só."""
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)",
            (usuario_id, total))
        pedido_id = cur.lastrowid
        db.executemany(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario)"
            " VALUES (?, ?, ?, ?)",
            [(pedido_id, i["produto_id"], i["quantidade"], i["preco_unitario"]) for i in itens])
        db.executemany(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
            [(i["quantidade"], i["produto_id"]) for i in itens])
        db.commit()
        return pedido_id
    except Exception:
        db.rollback()
        raise


def atualizar_status(pedido_id, status) -> None:
    db = get_db()
    db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (status, pedido_id))
    db.commit()


def totais():
    """Uma consulta agregada no lugar das cinco que existiam."""
    row = get_db().execute("""
        SELECT COUNT(*) AS total_pedidos,
               COALESCE(SUM(total), 0) AS faturamento,
               SUM(status = 'pendente')  AS pendentes,
               SUM(status = 'aprovado')  AS aprovados,
               SUM(status = 'cancelado') AS cancelados
          FROM pedidos""").fetchone()
    return {k: (row[k] or 0) for k in
            ("total_pedidos", "faturamento", "pendentes", "aprovados", "cancelados")}
