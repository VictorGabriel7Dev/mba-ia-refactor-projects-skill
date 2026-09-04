"""Mapeamento HTTP -> controller para usuários e login."""
from flask import Blueprint, jsonify, request

from controllers import user_controller

user_bp = Blueprint('users', __name__)


@user_bp.get('/users')
def get_users():
    return jsonify(user_controller.listar()), 200


@user_bp.get('/users/<int:user_id>')
def get_user(user_id):
    return jsonify(user_controller.obter(user_id)), 200


@user_bp.post('/users')
def create_user():
    return jsonify(user_controller.criar(request.get_json(silent=True))), 201


@user_bp.put('/users/<int:user_id>')
def update_user(user_id):
    return jsonify(user_controller.atualizar(user_id, request.get_json(silent=True))), 200


@user_bp.delete('/users/<int:user_id>')
def delete_user(user_id):
    user_controller.deletar(user_id)
    return jsonify({'message': 'Usuário deletado com sucesso'}), 200


@user_bp.get('/users/<int:user_id>/tasks')
def get_user_tasks(user_id):
    return jsonify(user_controller.tarefas_do_usuario(user_id)), 200


@user_bp.post('/login')
def login():
    usuario = user_controller.autenticar(request.get_json(silent=True))
    return jsonify({
        'message': 'Login realizado com sucesso',
        'user': usuario.to_dict(),
        'token': 'fake-jwt-token-' + str(usuario.id),
    }), 200
