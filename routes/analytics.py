from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from models import Analytics

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/admin/analytics', methods=['GET'])
@jwt_required()
def get_analytics():
    """Obtener estadísticas del sitio"""
    try:
        stats = Analytics.get_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500