"""Valores de domínio que antes eram literais espalhados pelo código."""

CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
STATUS_PEDIDO_VALIDOS = ("pendente", "aprovado", "enviado", "entregue", "cancelado")

NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200

# (piso de faturamento, taxa de desconto). Avaliado do maior para o menor.
FAIXAS_DESCONTO = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))
