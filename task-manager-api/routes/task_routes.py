"""Mapeamento HTTP -> controller. Zero consulta, zero cálculo.

Antes este arquivo tinha 299 linhas com a regra de negócio dentro dos handlers.
"""
from flask import Blueprint, jsonify, request

from controllers import task_controller

task_bp = Blueprint('tasks', __name__)


@task_bp.get('/tasks')
def get_tasks():
    return jsonify(task_controller.listar()), 200


@task_bp.get('/tasks/search')
def search_tasks():
    return jsonify(task_controller.buscar(
        request.args.get('q'), request.args.get('status'),
        request.args.get('priority'), request.args.get('user_id'))), 200


@task_bp.get('/tasks/stats')
def task_stats():
    return jsonify(task_controller.estatisticas()), 200


@task_bp.get('/tasks/<int:task_id>')
def get_task(task_id):
    return jsonify(task_controller.obter(task_id)), 200


@task_bp.post('/tasks')
def create_task():
    return jsonify(task_controller.criar(request.get_json(silent=True))), 201


@task_bp.put('/tasks/<int:task_id>')
def update_task(task_id):
    return jsonify(task_controller.atualizar(task_id, request.get_json(silent=True))), 200


@task_bp.delete('/tasks/<int:task_id>')
def delete_task(task_id):
    task_controller.deletar(task_id)
    return jsonify({'message': 'Task deletada com sucesso'}), 200
