"""Conexão com o banco, uma por requisição.

Antes havia uma conexão global de módulo aberta com `check_same_thread=False` e
compartilhada por todas as requisições. Agora cada requisição abre a sua, guardada
no contexto de aplicação do Flask (`g`), e o `teardown` fecha. Fora de requisição
(scripts, testes) a função devolve uma conexão avulsa que o chamador fecha.
"""
import sqlite3

from flask import g

from config import settings
from security import hash_senha


def conectar() -> sqlite3.Connection:
    con = sqlite3.connect(settings.DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def get_db() -> sqlite3.Connection:
    if "_db" not in g:
        g._db = conectar()
    return g._db


def fechar_db(_=None) -> None:
    con = g.pop("_db", None)
    if con is not None:
        con.close()


def registrar(app) -> None:
    app.teardown_appcontext(fechar_db)


ESQUEMA = (
    """CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, descricao TEXT,
        preco REAL, estoque INTEGER, categoria TEXT, ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, email TEXT, senha TEXT,
        tipo TEXT DEFAULT 'cliente', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER,
        status TEXT DEFAULT 'pendente', total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER, produto_id INTEGER,
        quantidade INTEGER, preco_unitario REAL)""",
)

PRODUTOS_INICIAIS = [
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
]

# As senhas de exemplo entram JÁ DERIVADAS. Antes iam em texto plano para o banco.
USUARIOS_INICIAIS = [
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
]


def inicializar() -> None:
    """Cria o esquema e semeia dados de exemplo. Idempotente."""
    con = conectar()
    try:
        cur = con.cursor()
        for ddl in ESQUEMA:
            cur.execute(ddl)
        con.commit()

        cur.execute("SELECT COUNT(*) FROM produtos")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO produtos (nome, descricao, preco, estoque, categoria)"
                " VALUES (?, ?, ?, ?, ?)", PRODUTOS_INICIAIS)
            cur.executemany(
                "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                [(n, e, hash_senha(s), t) for n, e, s, t in USUARIOS_INICIAIS])
            con.commit()
    finally:
        con.close()
