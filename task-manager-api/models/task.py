from config.constants import PRIORIDADE_MAX, PRIORIDADE_MIN, STATUS_FINAIS, STATUS_VALIDOS
from database import db
from utils.tempo import agora_utc


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default='pending')
    priority = db.Column(db.Integer, default=3)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=agora_utc)
    updated_at = db.Column(db.DateTime, default=agora_utc, onupdate=agora_utc)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    user = db.relationship('User', backref='tasks')
    category = db.relationship('Category', backref='tasks')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'user_id': self.user_id,
            'category_id': self.category_id,
            'created_at': str(self.created_at),
            'updated_at': str(self.updated_at),
            'due_date': str(self.due_date) if self.due_date else None,
            'tags': self.tags.split(',') if self.tags else [],
        }

    @staticmethod
    def validate_status(novo_status):
        return novo_status in STATUS_VALIDOS

    @staticmethod
    def validate_priority(p):
        return isinstance(p, int) and PRIORIDADE_MIN <= p <= PRIORIDADE_MAX

    def is_overdue(self):
        """A regra de atraso mora AQUI, e não copiada em quatro rotas.

        Antes este mesmo `if` aninhado aparecia em `task_routes` (3 vezes),
        `user_routes` e `report_routes` (2 vezes), cada cópia livre para divergir.
        """
        if not self.due_date:
            return False
        return self.due_date < agora_utc() and self.status not in STATUS_FINAIS
