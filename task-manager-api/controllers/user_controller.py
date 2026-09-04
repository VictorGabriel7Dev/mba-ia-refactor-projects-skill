"""Regra de negócio de usuário e autenticação."""
import re

from config.constants import ROLES_VALIDOS, SENHA_MIN
from database import db
from middlewares.error_handler import ErroDeAplicacao
from models.task import Task
from models.user import User

_EMAIL = re.compile(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$')


def _email(valor):
    if not _EMAIL.match(valor or ''):
        raise ErroDeAplicacao('Email inválido')
    return valor


def _senha(valor):
    if not valor or len(valor) < SENHA_MIN:
        raise ErroDeAplicacao(f'Senha deve ter ao menos {SENHA_MIN} caracteres')
    return valor


def _obter(user_id):
    usuario = db.session.get(User, user_id)
    if not usuario:
        raise ErroDeAplicacao('Usuário não encontrado', 404)
    return usuario


def listar():
    """Contagem de tarefas por usuário em UMA consulta agregada.

    Antes era `len(u.tasks)` dentro do laço, o que dispara uma consulta por
    usuário por causa do lazy loading do relacionamento.
    """
    linhas = (db.session.query(User, db.func.count(Task.id))
              .outerjoin(Task, Task.user_id == User.id).group_by(User.id).all())
    return [{**u.to_dict(), 'task_count': n} for u, n in linhas]


def obter(user_id):
    usuario = _obter(user_id)
    tarefas = Task.query.filter_by(user_id=user_id).all()
    return {**usuario.to_dict(), 'tasks': [t.to_dict() for t in tarefas]}


def tarefas_do_usuario(user_id):
    _obter(user_id)
    saida = []
    for t in Task.query.filter_by(user_id=user_id).all():
        dados = t.to_dict()
        dados['overdue'] = t.is_overdue()
        saida.append(dados)
    return saida


def criar(dados):
    if not dados:
        raise ErroDeAplicacao('Dados inválidos')
    nome = dados.get('name')
    if not nome:
        raise ErroDeAplicacao('Nome é obrigatório')
    email = _email(dados.get('email'))
    if User.query.filter_by(email=email).first():
        raise ErroDeAplicacao('Email já cadastrado', 409)

    usuario = User()
    usuario.name = nome
    usuario.email = email
    usuario.set_password(_senha(dados.get('password')))
    papel = dados.get('role', 'user')
    if papel not in ROLES_VALIDOS:
        raise ErroDeAplicacao('Role inválido')
    usuario.role = papel

    db.session.add(usuario)
    db.session.commit()
    return usuario.to_dict()


def atualizar(user_id, dados):
    usuario = _obter(user_id)
    if not dados:
        raise ErroDeAplicacao('Dados inválidos')

    if 'name' in dados:
        usuario.name = dados['name']
    if 'email' in dados:
        email = _email(dados['email'])
        existente = User.query.filter_by(email=email).first()
        if existente and existente.id != user_id:
            raise ErroDeAplicacao('Email já cadastrado', 409)
        usuario.email = email
    if 'password' in dados:
        usuario.set_password(_senha(dados['password']))
    if 'role' in dados:
        if dados['role'] not in ROLES_VALIDOS:
            raise ErroDeAplicacao('Role inválido')
        usuario.role = dados['role']
    if 'active' in dados:
        usuario.active = dados['active']

    db.session.commit()
    return usuario.to_dict()


def deletar(user_id):
    usuario = _obter(user_id)
    db.session.delete(usuario)
    db.session.commit()


def autenticar(dados):
    if not dados:
        raise ErroDeAplicacao('Dados inválidos')
    email, senha = dados.get('email'), dados.get('password')
    if not email or not senha:
        raise ErroDeAplicacao('Email e senha são obrigatórios')

    usuario = User.query.filter_by(email=email).first()
    # Mensagem única para usuário inexistente e senha errada: distinguir os dois
    # entrega quais e-mails existem na base.
    if not usuario or not usuario.check_password(senha):
        raise ErroDeAplicacao('Credenciais inválidas', 401)
    if not usuario.active:
        raise ErroDeAplicacao('Usuário inativo', 403)
    return usuario
