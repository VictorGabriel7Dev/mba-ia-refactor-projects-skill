"""Regra de negócio de tarefa. Não conhece `request` nem `jsonify`."""
from datetime import datetime

from config.constants import (FORMATOS_DATA, PRIORIDADE_MAX, PRIORIDADE_MIN, STATUS_FINAIS,
                              STATUS_VALIDOS, TITULO_MAX, TITULO_MIN)
from database import db
from middlewares.error_handler import ErroDeAplicacao
from models.category import Category
from models.task import Task
from models.user import User
from utils.tempo import agora_utc


def _parse_data(valor):
    for formato in FORMATOS_DATA:
        try:
            return datetime.strptime(valor, formato)
        except (TypeError, ValueError):
            continue
    raise ErroDeAplicacao('Formato de data inválido. Use YYYY-MM-DD')


def _titulo(valor):
    if not valor:
        raise ErroDeAplicacao('Título é obrigatório')
    if len(valor) < TITULO_MIN:
        raise ErroDeAplicacao('Título muito curto')
    if len(valor) > TITULO_MAX:
        raise ErroDeAplicacao('Título muito longo')
    return valor


def _prioridade(valor):
    if not isinstance(valor, int) or isinstance(valor, bool):
        raise ErroDeAplicacao('Prioridade deve ser um número inteiro')
    if not PRIORIDADE_MIN <= valor <= PRIORIDADE_MAX:
        raise ErroDeAplicacao(f'Prioridade deve ser entre {PRIORIDADE_MIN} e {PRIORIDADE_MAX}')
    return valor


def _status(valor):
    if valor not in STATUS_VALIDOS:
        raise ErroDeAplicacao('Status inválido')
    return valor


def _relacionado(modelo, ident, rotulo):
    if ident is None:
        return None
    obj = db.session.get(modelo, ident)
    if not obj:
        raise ErroDeAplicacao(f'{rotulo} não encontrado', 404)
    return obj


def _tags(valor):
    return ','.join(valor) if isinstance(valor, list) else valor


def listar():
    """Uma consulta com JOIN, no lugar de 1 + 2N.

    A rota antiga buscava usuário e categoria de CADA tarefa dentro do laço.
    """
    linhas = (db.session.query(Task, User.name, Category.name)
              .outerjoin(User, User.id == Task.user_id)
              .outerjoin(Category, Category.id == Task.category_id).all())
    saida = []
    for tarefa, nome_usuario, nome_categoria in linhas:
        dados = tarefa.to_dict()
        dados['overdue'] = tarefa.is_overdue()
        dados['user_name'] = nome_usuario
        dados['category_name'] = nome_categoria
        saida.append(dados)
    return saida


def obter(task_id):
    tarefa = db.session.get(Task, task_id)
    if not tarefa:
        raise ErroDeAplicacao('Task não encontrada', 404)
    dados = tarefa.to_dict()
    dados['overdue'] = tarefa.is_overdue()
    return dados


def criar(dados):
    if not dados:
        raise ErroDeAplicacao('Dados inválidos')

    tarefa = Task()
    tarefa.title = _titulo(dados.get('title'))
    tarefa.description = dados.get('description', '')
    tarefa.status = _status(dados.get('status', 'pending'))
    tarefa.priority = _prioridade(dados.get('priority', 3))
    tarefa.user_id = dados.get('user_id')
    tarefa.category_id = dados.get('category_id')
    _relacionado(User, tarefa.user_id, 'Usuário')
    _relacionado(Category, tarefa.category_id, 'Categoria')
    if dados.get('due_date'):
        tarefa.due_date = _parse_data(dados['due_date'])
    if dados.get('tags'):
        tarefa.tags = _tags(dados['tags'])

    db.session.add(tarefa)
    db.session.commit()
    return tarefa.to_dict()


def atualizar(task_id, dados):
    tarefa = db.session.get(Task, task_id)
    if not tarefa:
        raise ErroDeAplicacao('Task não encontrada', 404)
    if not dados:
        raise ErroDeAplicacao('Dados inválidos')

    if 'title' in dados:
        tarefa.title = _titulo(dados['title'])
    if 'description' in dados:
        tarefa.description = dados['description']
    if 'status' in dados:
        tarefa.status = _status(dados['status'])
    if 'priority' in dados:
        tarefa.priority = _prioridade(dados['priority'])
    if 'user_id' in dados:
        _relacionado(User, dados['user_id'], 'Usuário')
        tarefa.user_id = dados['user_id']
    if 'category_id' in dados:
        _relacionado(Category, dados['category_id'], 'Categoria')
        tarefa.category_id = dados['category_id']
    if 'due_date' in dados:
        tarefa.due_date = _parse_data(dados['due_date']) if dados['due_date'] else None
    if 'tags' in dados:
        tarefa.tags = _tags(dados['tags'])

    tarefa.updated_at = agora_utc()
    db.session.commit()
    return tarefa.to_dict()


def deletar(task_id):
    tarefa = db.session.get(Task, task_id)
    if not tarefa:
        raise ErroDeAplicacao('Task não encontrada', 404)
    db.session.delete(tarefa)
    db.session.commit()


def buscar(termo=None, status=None, prioridade=None, user_id=None):
    consulta = Task.query
    if termo:
        consulta = consulta.filter(db.or_(Task.title.like(f'%{termo}%'),
                                          Task.description.like(f'%{termo}%')))
    if status:
        consulta = consulta.filter(Task.status == status)
    for valor, coluna, rotulo in ((prioridade, Task.priority, 'priority'),
                                  (user_id, Task.user_id, 'user_id')):
        if valor:
            try:
                consulta = consulta.filter(coluna == int(valor))
            except (TypeError, ValueError):
                raise ErroDeAplicacao(f'{rotulo} deve ser numérico')
    return [t.to_dict() for t in consulta.all()]


def estatisticas():
    """Uma consulta agregada, no lugar de 5 contagens mais um laço em memória."""
    contagem = dict(db.session.query(Task.status, db.func.count(Task.id))
                    .group_by(Task.status).all())
    total = sum(contagem.values())
    atrasadas = (Task.query
                 .filter(Task.due_date.isnot(None), Task.due_date < agora_utc(),
                         Task.status.notin_(STATUS_FINAIS)).count())
    feitas = contagem.get('done', 0)
    return {
        'total': total,
        'pending': contagem.get('pending', 0),
        'in_progress': contagem.get('in_progress', 0),
        'done': feitas,
        'cancelled': contagem.get('cancelled', 0),
        'overdue': atrasadas,
        'completion_rate': round((feitas / total) * 100, 2) if total else 0,
    }
