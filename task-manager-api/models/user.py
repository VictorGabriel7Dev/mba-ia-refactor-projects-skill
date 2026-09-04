from database import db
from security import hash_senha, verificar_senha
from utils.tempo import agora_utc


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=agora_utc)

    def to_dict(self):
        """Representação PÚBLICA.

        A versão anterior incluía o campo `password`, e como este método é usado
        por `GET /users/<id>` e pela resposta do `POST /login`, o hash saía em toda
        rota que serializasse um usuário. Campo sensível não entra aqui.
        """
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'active': self.active,
            'created_at': str(self.created_at),
        }

    def set_password(self, pwd):
        self.password = hash_senha(pwd)

    def check_password(self, pwd):
        return verificar_senha(pwd, self.password)

    def is_admin(self):
        return self.role == 'admin'
