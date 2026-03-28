from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import User, History
from auth import get_current_user, hash_password, check_password

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/api/admin/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Cambiar contraseña del usuario actual"""
    try:
        user = get_current_user()
        data = request.json
        
        if not all(key in data for key in ['current_password', 'new_password']):
            return jsonify({'error': 'Faltan campos requeridos'}), 400
        
        # Verificar contraseña actual
        user_data = User.find_by_username(user)
        if not check_password(data['current_password'], user_data['password']):
            return jsonify({'error': 'Contraseña actual incorrecta'}), 401
        
        # Actualizar contraseña
        new_hash = hash_password(data['new_password'])
        User.update_password(user, new_hash)
        
        # Registrar en historial
        History.log_action(
            user=user,
            action='update',
            entity_type='user',
            entity_id=user,
            details={'action': 'cambió contraseña'}
        )
        
        return jsonify({'success': True, 'message': 'Contraseña actualizada'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/history', methods=['GET'])
@jwt_required()
def get_history():
    """Obtener historial de cambios"""
    try:
        limit = request.args.get('limit', 50, type=int)
        history = History.get_recent(limit)
        return jsonify(history), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/users', methods=['GET'])
@jwt_required()
def get_users():
    """Obtener lista de usuarios (sin contraseñas)"""
    try:
        # Por ahora retornamos info básica
        # En el futuro se puede expandir para crear/editar usuarios
        user = get_current_user()
        user_data = User.find_by_username(user)
        
        return jsonify({
            'username': user_data['username'],
            'role': user_data['role']
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500