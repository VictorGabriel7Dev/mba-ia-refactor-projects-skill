"""Mapeamento HTTP -> controller para relatórios e categorias."""
from flask import Blueprint, jsonify, request

from controllers import category_controller, report_controller

report_bp = Blueprint('reports', __name__)


@report_bp.get('/reports/summary')
def summary_report():
    return jsonify(report_controller.resumo()), 200


@report_bp.get('/reports/user/<int:user_id>')
def user_report(user_id):
    return jsonify(report_controller.por_usuario(user_id)), 200


@report_bp.get('/categories')
def get_categories():
    return jsonify(category_controller.listar()), 200


@report_bp.post('/categories')
def create_category():
    return jsonify(category_controller.criar(request.get_json(silent=True))), 201


@report_bp.put('/categories/<int:cat_id>')
def update_category(cat_id):
    return jsonify(category_controller.atualizar(cat_id, request.get_json(silent=True))), 200


@report_bp.delete('/categories/<int:cat_id>')
def delete_category(cat_id):
    category_controller.deletar(cat_id)
    return jsonify({'message': 'Categoria deletada'}), 200
