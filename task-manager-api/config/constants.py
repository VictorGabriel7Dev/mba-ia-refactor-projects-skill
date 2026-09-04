"""Valores de domínio que antes eram literais repetidos em três arquivos."""

STATUS_VALIDOS = ("pending", "in_progress", "done", "cancelled")
STATUS_FINAIS = ("done", "cancelled")
ROLES_VALIDOS = ("user", "admin", "manager")

TITULO_MIN = 3
TITULO_MAX = 200
PRIORIDADE_MIN = 1
PRIORIDADE_MAX = 5
PRIORIDADE_PADRAO = 3
# Era 4. Quatro caracteres não é política de senha, é enfeite.
SENHA_MIN = 8
COR_PADRAO = "#000000"

FORMATOS_DATA = ("%Y-%m-%d", "%d/%m/%Y")
