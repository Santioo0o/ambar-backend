from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os
from dotenv import load_dotenv
import cloudinary

# Cargar variables de entorno
load_dotenv()

# Importar rutas y auth
from routes.products import products_bp
from routes.admin import admin_bp
from routes.analytics import analytics_bp
from auth import login_user, create_initial_users

# Crear app
app = Flask(__name__)

# Configuración
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# CORS - permite que el frontend se comunique con el backend
CORS(app, resources={
    r"/api/*": {
        "origins": "*",  # En producción cambiar a tu dominio específico
        "methods": ["GET", "POST", "PUT", "DELETE", "PATCH"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# JWT
jwt = JWTManager(app)

# Configurar Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Registrar blueprints (rutas)
app.register_blueprint(products_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(analytics_bp)

# Ruta de login
@app.route('/api/login', methods=['POST'])
def login():
    """Endpoint de login"""
    data = request.json
    
    if not all(key in data for key in ['username', 'password']):
        return jsonify({'error': 'Faltan credenciales'}), 400
    
    result, status = login_user(data['username'], data['password'])
    return jsonify(result), status

# Health check (para verificar que el servidor está despierto)
@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint para verificar que el servidor está funcionando"""
    return jsonify({
        'status': 'ok',
        'message': 'Servidor funcionando correctamente'
    }), 200

# Ruta raíz
@app.route('/')
def index():
    return jsonify({
        'message': 'API de Ambar Aromatizantes',
        'version': '1.0',
        'endpoints': {
            'health': '/api/health',
            'login': '/api/login',
            'products': '/api/products',
            'admin': '/api/admin/*'
        }
    })

# Manejo de errores
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint no encontrado'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Error interno del servidor'}), 500

# Inicialización de usuarios para asegurar que existan en Atlas cuando se despliega en Render
try:
    with app.app_context():
        create_initial_users()
except Exception as e:
    print("Warning: Could not create initial users:", e)

if __name__ == '__main__':
    # Iniciar servidor local
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)