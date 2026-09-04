"""Regra de negócio de categoria."""
from config.constants import COR_PADRAO
from database import db
from middlewares.error_handler import ErroDeAplicacao
from models.category import Category
from models.task import Task


def _obter(cat_id):
    categoria = db.session.get(Category, cat_id)
    if not categoria:
        raise ErroDeAplicacao('Categoria não encontrada', 404)
    return categoria


def listar():
    """Contagem por categoria em UMA consulta agregada, e não uma por categoria."""
    linhas = (db.session.query(Category, db.func.count(Task.id))
              .outerjoin(Task, Task.category_id == Category.id).group_by(Category.id).all())
    return [{**c.to_dict(), 'task_count': n} for c, n in linhas]


def criar(dados):
    if not dados:
        raise ErroDeAplicacao('Dados inválidos')
    nome = dados.get('name')
    if not nome:
        raise ErroDeAplicacao('Nome é obrigatório')

    categoria = Category()
    categoria.name = nome
    categoria.description = dados.get('description', '')
    categoria.color = dados.get('color', COR_PADRAO)
    db.session.add(categoria)
    db.session.commit()
    return categoria.to_dict()


def atualizar(cat_id, dados):
    categoria = _obter(cat_id)
    for campo in ('name', 'description', 'color'):
        if campo in (dados or {}):
            setattr(categoria, campo, dados[campo])
    db.session.commit()
    return categoria.to_dict()


def deletar(cat_id):
    categoria = _obter(cat_id)
    db.session.delete(categoria)
    db.session.commit()
