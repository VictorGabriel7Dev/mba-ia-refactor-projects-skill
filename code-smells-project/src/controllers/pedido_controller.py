"""Regra de negócio de pedido e relatório de vendas."""
from config.constants import FAIXAS_DESCONTO, STATUS_PEDIDO_VALIDOS
from middlewares.error_handler import ErroDeAplicacao
from models import pedido_model


def criar(dados):
    if not dados:
        raise ErroDeAplicacao("Dados inválidos")
    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])
    if not usuario_id:
        raise ErroDeAplicacao("Usuario ID é obrigatório")
    if not itens:
        raise ErroDeAplicacao("Pedido deve ter pelo menos 1 item")

    # Uma consulta para todos os produtos do pedido, no lugar de uma por item.
    catalogo = pedido_model.produtos_por_ids({i.get("produto_id") for i in itens})

    total, linhas = 0.0, []
    for item in itens:
        produto = catalogo.get(item.get("produto_id"))
        if produto is None:
            raise ErroDeAplicacao(f"Produto {item.get('produto_id')} não encontrado")
        if produto["estoque"] < item.get("quantidade", 0):
            raise ErroDeAplicacao(f"Estoque insuficiente para {produto['nome']}")
        total += produto["preco"] * item["quantidade"]
        linhas.append({"produto_id": produto["id"], "quantidade": item["quantidade"],
                       "preco_unitario": produto["preco"]})

    pedido_id = pedido_model.registrar(usuario_id, total, linhas)
    return {"pedido_id": pedido_id, "total": total}


def listar():
    return pedido_model.listar()


def por_usuario(usuario_id):
    return pedido_model.por_usuario(usuario_id)


def atualizar_status(pedido_id, dados):
    status = (dados or {}).get("status", "")
    if status not in STATUS_PEDIDO_VALIDOS:
        raise ErroDeAplicacao("Status inválido")
    pedido_model.atualizar_status(pedido_id, status)


def _desconto(faturamento: float) -> float:
    for piso, taxa in FAIXAS_DESCONTO:
        if faturamento > piso:
            return faturamento * taxa
    return 0.0


def relatorio_vendas():
    t = pedido_model.totais()
    faturamento = float(t["faturamento"])
    desconto = _desconto(faturamento)
    return {
        "total_pedidos": t["total_pedidos"],
        "faturamento_bruto": round(faturamento, 2),
        "desconto_aplicavel": round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes": t["pendentes"],
        "pedidos_aprovados": t["aprovados"],
        "pedidos_cancelados": t["cancelados"],
        "ticket_medio": round(faturamento / t["total_pedidos"], 2) if t["total_pedidos"] else 0,
    }


def health():
    """Diagnóstico. NÃO devolve segredo nem caminho de arquivo: a versão anterior
    entregava `secret_key`, `db_path` e `debug` a qualquer requisição anônima."""
    from models import produto_model, usuario_model
    return {
        "status": "ok",
        "database": "connected",
        "counts": {
            "produtos": len(produto_model.listar()),
            "usuarios": len(usuario_model.listar()),
            "pedidos": pedido_model.totais()["total_pedidos"],
        },
        "versao": "1.0.0",
    }
