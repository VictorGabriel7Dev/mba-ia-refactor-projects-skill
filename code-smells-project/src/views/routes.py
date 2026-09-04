"""Mapeamento HTTP -> controller. Zero consulta a banco, zero cálculo.

Os caminhos, métodos, formato de resposta e códigos de status são exatamente os de
antes. As duas rotas administrativas (`/admin/query` e `/admin/reset-db`) foram
REMOVIDAS de propósito: a primeira executava SQL arbitrário e a segunda apagava as
quatro tabelas, ambas sem autenticação.
"""
from flask import Blueprint, jsonify, request

from controllers import pedido_controller, produto_controller, usuario_controller

bp = Blueprint("api", __name__)


def ok(dados, status=200, **extra):
    return jsonify({"dados": dados, "sucesso": True, **extra}), status


@bp.get("/")
def index():
    return jsonify({
        "mensagem": "Bem-vindo à API da Loja",
        "versao": "1.0.0",
        "endpoints": {
            "produtos": "/produtos", "usuarios": "/usuarios", "pedidos": "/pedidos",
            "login": "/login", "relatorios": "/relatorios/vendas", "health": "/health",
        },
    })


@bp.get("/health")
def health():
    return jsonify(pedido_controller.health()), 200


@bp.get("/produtos")
def listar_produtos():
    return ok(produto_controller.listar())


@bp.get("/produtos/busca")
def buscar_produtos():
    resultados = produto_controller.buscar(
        request.args.get("q", ""), request.args.get("categoria"),
        request.args.get("preco_min"), request.args.get("preco_max"))
    return ok(resultados, total=len(resultados))


@bp.get("/produtos/<int:id>")
def buscar_produto(id):
    return ok(produto_controller.obter(id))


@bp.post("/produtos")
def criar_produto():
    return ok(produto_controller.criar(request.get_json(silent=True)), 201,
              mensagem="Produto criado")


@bp.put("/produtos/<int:id>")
def atualizar_produto(id):
    produto_controller.atualizar(id, request.get_json(silent=True))
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


@bp.delete("/produtos/<int:id>")
def deletar_produto(id):
    produto_controller.deletar(id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200


@bp.get("/usuarios")
def listar_usuarios():
    return ok(usuario_controller.listar())


@bp.get("/usuarios/<int:id>")
def buscar_usuario(id):
    return ok(usuario_controller.obter(id))


@bp.post("/usuarios")
def criar_usuario():
    return ok(usuario_controller.criar(request.get_json(silent=True)), 201)


@bp.post("/login")
def login():
    return ok(usuario_controller.autenticar(request.get_json(silent=True)),
              mensagem="Login OK")


@bp.post("/pedidos")
def criar_pedido():
    return ok(pedido_controller.criar(request.get_json(silent=True)), 201,
              mensagem="Pedido criado com sucesso")


@bp.get("/pedidos")
def listar_todos_pedidos():
    return ok(pedido_controller.listar())


@bp.get("/pedidos/usuario/<int:usuario_id>")
def listar_pedidos_usuario(usuario_id):
    return ok(pedido_controller.por_usuario(usuario_id))


@bp.put("/pedidos/<int:pedido_id>/status")
def atualizar_status_pedido(pedido_id):
    pedido_controller.atualizar_status(pedido_id, request.get_json(silent=True))
    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200


@bp.get("/relatorios/vendas")
def relatorio_vendas():
    return ok(pedido_controller.relatorio_vendas())
