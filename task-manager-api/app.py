"""Composition root: monta a aplicação e conecta as camadas. Nenhuma regra aqui."""
from flask import Flask, jsonify
from flask_cors import CORS

from config import settings
from database import db
from middlewares import error_handler
from routes.report_routes import report_bp
from routes.task_routes import task_bp
from routes.user_routes import user_bp
from services.notification_service import NotificationService
from utils.tempo import agora_utc


def criar_servico_notificacao() -> NotificationService:
    return NotificationService(settings.EMAIL_HOST, settings.EMAIL_PORT,
                               settings.EMAIL_USER, settings.EMAIL_PASSWORD)


def criar_app() -> Flask:
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = settings.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['SECRET_KEY'] = settings.SECRET_KEY

    CORS(app, origins=settings.CORS_ORIGENS)
    db.init_app(app)
    error_handler.registrar(app)

    app.register_blueprint(task_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(report_bp)

    app.extensions['notificacao'] = criar_servico_notificacao()

    @app.get('/health')
    def health():
        return jsonify({'status': 'ok', 'timestamp': str(agora_utc())})

    @app.get('/')
    def index():
        return jsonify({'message': 'Task Manager API', 'version': '1.0'})

    with app.app_context():
        db.create_all()
    return app


app = criar_app()

if __name__ == '__main__':
    app.run(debug=settings.DEBUG, host=settings.HOST, port=settings.PORT)
