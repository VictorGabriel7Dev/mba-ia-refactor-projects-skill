"""Regra de negócio de produto. Não conhece `request` nem `jsonify`."""
from config.constants import CATEGORIAS_VALIDAS, NOME_PRODUTO_MAX, NOME_PRODUTO_MIN
from middlewares.error_handler import ErroDeAplicacao
from models import produto_model


def _numero(valor, campo):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ErroDeAplicacao(f"{campo} deve ser numérico")
    return valor


def _validar(dados):
    if not dados:
        raise ErroDeAplicacao("Dados inválidos")
    for obrigatorio, rotulo in (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque")):
        if obrigatorio not in dados:
            raise ErroDeAplicacao(f"{rotulo} é obrigatório")

    nome = dados["nome"]
    preco = _numero(dados["preco"], "Preço")
    estoque = _numero(dados["estoque"], "Estoque")
    categoria = dados.get("categoria", "geral")

    if preco < 0:
        raise ErroDeAplicacao("Preço não pode ser negativo")
    if estoque < 0:
        raise ErroDeAplicacao("Estoque não pode ser negativo")
    if len(nome) < NOME_PRODUTO_MIN:
        raise ErroDeAplicacao("Nome muito curto")
    if len(nome) > NOME_PRODUTO_MAX:
        raise ErroDeAplicacao("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ErroDeAplicacao("Categoria inválida. Válidas: " + str(list(CATEGORIAS_VALIDAS)))
    return nome, dados.get("descricao", ""), preco, estoque, categoria


def listar():
    return produto_model.listar()


def obter(produto_id):
    produto = produto_model.por_id(produto_id)
    if not produto:
        raise ErroDeAplicacao("Produto não encontrado", 404)
    return produto


def criar(dados):
    return {"id": produto_model.criar(*_validar(dados))}


def atualizar(produto_id, dados):
    obter(produto_id)
    produto_model.atualizar(produto_id, *_validar(dados))


def deletar(produto_id):
    obter(produto_id)
    produto_model.deletar(produto_id)


def buscar(termo, categoria, preco_min, preco_max):
    def _decimal(valor, campo):
        if valor in (None, ""):
            return None
        try:
            return float(valor)
        except (TypeError, ValueError):
            raise ErroDeAplicacao(f"{campo} deve ser numérico")

    return produto_model.buscar(termo, categoria,
                                _decimal(preco_min, "preco_min"),
                                _decimal(preco_max, "preco_max"))
