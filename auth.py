import bcrypt
from flask import jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity
from models import User
from datetime import timedelta

def hash_password(password):
    """Hashear contraseña"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    """Verificar contraseña"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def login_user(username, password):
    """Autenticar usuario y generar token"""
    user = User.find_by_username(username)
    
    if not user:
        return {'error': 'Usuario no encontrado'}, 404
    
    if not check_password(password, user['password']):
        return {'error': 'Contraseña incorrecta'}, 401
    
    # Crear token JWT válido por 24 horas
    access_token = create_access_token(
        identity=username,
        expires_delta=timedelta(hours=24)
    )
    
    return {
        'access_token': access_token,
        'username': username,
        'role': user['role']
    }, 200

def create_initial_users():
    """Crear usuarios iniciales si no existen"""
    # Usuario: Juli
    if not User.find_by_username('Juli'):
        hashed = hash_password('S4nt14g0')
        User.create('Juli', hashed, 'admin')
        print("✅ Usuario 'Juli' creado")

    # Usuario: Santi
    if not User.find_by_username('Santi'):
        hashed = hash_password('S4nt14g0')
        User.create('Santi', hashed, 'admin')
        print("✅ Usuario 'Santi' creado")

    # Puedes agregar más usuarios aquí si quieres
    # if not User.find_by_username('mama'):
    #     hashed = hash_password('otracontraseña')
    #     User.create('mama', hashed, 'admin')
    #     print("✅ Usuario 'mama' creado")

def get_current_user():
    """Obtener usuario actual del token"""
    return get_jwt_identity()