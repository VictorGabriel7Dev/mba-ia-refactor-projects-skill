"""Relatórios. Toda a agregação que estava dentro dos handlers mora aqui."""
from datetime import timedelta

from database import db
from middlewares.error_handler import ErroDeAplicacao
from models.category import Category
from models.task import Task
from models.user import User
from config.constants import STATUS_FINAIS
from utils.tempo import agora_utc


def _por_coluna(coluna):
    return dict(db.session.query(coluna, db.func.count(Task.id)).group_by(coluna).all())


def resumo():
    agora = agora_utc()
    por_status = _por_coluna(Task.status)
    por_prioridade = _por_coluna(Task.priority)

    atrasadas = (Task.query
                 .filter(Task.due_date.isnot(None), Task.due_date < agora,
                         Task.status.notin_(STATUS_FINAIS)).all())

    sete_dias = agora - timedelta(days=7)

    # Produtividade por usuário em UMA consulta agregada. Antes era um laço sobre
    # os usuários com uma consulta de tarefas por usuário dentro (N+1 clássico).
    linhas = (db.session.query(
        User.id, User.name,
        db.func.count(Task.id),
        db.func.sum(db.case((Task.status == 'done', 1), else_=0)))
        .outerjoin(Task, Task.user_id == User.id).group_by(User.id).all())

    return {
        'generated_at': str(agora),
        'overview': {
            'total_tasks': sum(por_status.values()),
            'total_users': User.query.count(),
            'total_categories': Category.query.count(),
        },
        'tasks_by_status': {s: por_status.get(s, 0)
                            for s in ('pending', 'in_progress', 'done', 'cancelled')},
        'tasks_by_priority': {
            'critical': por_prioridade.get(1, 0), 'high': por_prioridade.get(2, 0),
            'medium': por_prioridade.get(3, 0), 'low': por_prioridade.get(4, 0),
            'minimal': por_prioridade.get(5, 0),
        },
        'overdue': {
            'count': len(atrasadas),
            'tasks': [{'id': t.id, 'title': t.title, 'due_date': str(t.due_date),
                       'days_overdue': (agora - t.due_date).days} for t in atrasadas],
        },
        'recent_activity': {
            'tasks_created_last_7_days': Task.query.filter(Task.created_at >= sete_dias).count(),
            'tasks_completed_last_7_days': Task.query.filter(
                Task.status == 'done', Task.updated_at >= sete_dias).count(),
        },
        'user_productivity': [
            {'user_id': uid, 'user_name': nome, 'total_tasks': total,
             'completed_tasks': int(feitas or 0),
             'completion_rate': round((int(feitas or 0) / total) * 100, 2) if total else 0}
            for uid, nome, total, feitas in linhas
        ],
    }


def por_usuario(user_id):
    usuario = db.session.get(User, user_id)
    if not usuario:
        raise ErroDeAplicacao('Usuário não encontrado', 404)

    agora = agora_utc()
    tarefas = Task.query.filter_by(user_id=user_id).all()
    contagem = {s: 0 for s in ('done', 'pending', 'in_progress', 'cancelled')}
    alta, atrasadas = 0, 0
    for t in tarefas:
        if t.status in contagem:
            contagem[t.status] += 1
        if t.priority <= 2:
            alta += 1
        if t.due_date and t.due_date < agora and t.status not in STATUS_FINAIS:
            atrasadas += 1

    total = len(tarefas)
    return {
        'user': {'id': usuario.id, 'name': usuario.name, 'email': usuario.email},
        'statistics': {
            'total_tasks': total, **contagem, 'overdue': atrasadas, 'high_priority': alta,
            'completion_rate': round((contagem['done'] / total) * 100, 2) if total else 0,
        },
    }
