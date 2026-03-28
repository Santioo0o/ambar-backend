from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from models import Product, Batch, History, Analytics, Promotion
from auth import get_current_user
import cloudinary.uploader

products_bp = Blueprint('products', __name__)

# Rutas públicas
@products_bp.route('/api/products', methods=['GET'])
def get_products():
    """Obtener productos visibles"""
    try:
        Analytics.log_visit()
        products = Product.find_all(visible_only=True)
        return jsonify(products), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/products/<product_id>/view', methods=['POST'])
def log_product_view(product_id):
    """Registrar vista de producto"""
    try:
        product = Product.find_by_id(product_id)
        if product:
            Analytics.log_product_view(product_id, product['name'])
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/products/<product_id>/add-to-cart', methods=['POST'])
def log_add_to_cart(product_id):
    """Registrar cuando se agrega al carrito"""
    try:
        product = Product.find_by_id(product_id)
        if product:
            Analytics.log_add_to_cart(product_id, product['name'])
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/promotions/active', methods=['GET'])
def get_active_promotions():
    """Obtener promociones activas"""
    try:
        promotions = Promotion.find_active()
        return jsonify(promotions), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rutas de administración
@products_bp.route('/api/admin/products', methods=['GET'])
@jwt_required()
def get_all_products_admin():
    """Obtener TODOS los productos (admin)"""
    try:
        products = Product.find_all(visible_only=False)
        return jsonify(products), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/products', methods=['POST'])
@jwt_required()
def create_product():
    """Crear nuevo producto"""
    try:
        user = get_current_user()
        data = request.json
        
        if not all(key in data for key in ['name', 'category', 'price']):
            return jsonify({'error': 'Faltan campos requeridos'}), 400
        
        # Asegurar que images sea un array
        if 'images' not in data:
            data['images'] = [data.get('image', '')] if data.get('image') else []
        
        product = Product.create(data)
        
        History.log_action(
            user=user,
            action='create',
            entity_type='product',
            entity_id=product['_id'],
            details={'name': product['name']}
        )
        
        return jsonify(product), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/products/<product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    """Actualizar producto"""
    try:
        user = get_current_user()
        data = request.json
        
        old_product = Product.find_by_id(product_id)
        if not old_product:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        product = Product.update(product_id, data)
        
        History.log_action(
            user=user,
            action='update',
            entity_type='product',
            entity_id=product_id,
            details={'name': product['name']}
        )
        
        return jsonify(product), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/products/<product_id>/toggle', methods=['PATCH'])
@jwt_required()
def toggle_visibility(product_id):
    """Cambiar visibilidad del producto"""
    try:
        user = get_current_user()
        product = Product.find_by_id(product_id)
        
        if not product:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        new_visibility = not product['visible']
        Product.update(product_id, {'visible': new_visibility})
        
        History.log_action(
            user=user,
            action='update',
            entity_type='product',
            entity_id=product_id,
            details={
                'name': product['name'],
                'action': 'mostrar' if new_visibility else 'ocultar'
            }
        )
        
        return jsonify({'visible': new_visibility}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/products/<product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    """Eliminar producto"""
    try:
        user = get_current_user()
        product = Product.find_by_id(product_id)
        
        if not product:
            return jsonify({'error': 'Producto no encontrado'}), 404
        
        Product.delete(product_id)
        
        History.log_action(
            user=user,
            action='delete',
            entity_type='product',
            entity_id=product_id,
            details={'name': product['name']}
        )
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/upload-image', methods=['POST'])
@jwt_required()
def upload_image():
    """Subir imagen a Cloudinary"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se encontró archivo'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
        result = cloudinary.uploader.upload(
            file,
            folder='ambar_productos',
            transformation=[
                {'width': 800, 'height': 800, 'crop': 'limit'},
                {'quality': 'auto:good'}
            ]
        )
        
        return jsonify({'url': result['secure_url']}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rutas para lotes
@products_bp.route('/api/admin/products/<product_id>/batches', methods=['GET'])
@jwt_required()
def get_product_batches(product_id):
    """Obtener todos los lotes de un producto"""
    try:
        batches = Batch.find_by_product(product_id)
        return jsonify(batches), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/batches', methods=['POST'])
@jwt_required()
def create_batch():
    """Crear nuevo lote"""
    try:
        user = get_current_user()
        data = request.json
        
        if not all(key in data for key in ['product_id', 'quantity', 'expiry_date']):
            return jsonify({'error': 'Faltan campos requeridos'}), 400
        
        batch = Batch.create(data)
        
        product = Product.find_by_id(data['product_id'])
        History.log_action(
            user=user,
            action='create',
            entity_type='batch',
            entity_id=batch['_id'],
            details={
                'product_name': product['name'] if product else 'Desconocido',
                'quantity': data['quantity'],
                'expiry_date': data['expiry_date']
            }
        )
        
        return jsonify(batch), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/batches/<batch_id>', methods=['PUT'])
@jwt_required()
def update_batch(batch_id):
    """Actualizar lote"""
    try:
        user = get_current_user()
        data = request.json
        
        # Obtener el lote actual antes de modificar para capturar valores anteriores
        old_batch = Batch.find_by_id(batch_id)
        if not old_batch:
            return jsonify({'error': 'Lote no encontrado'}), 404
        
        # Obtener información del producto
        product = Product.find_by_id(old_batch['product_id'])
        product_name = product['name'] if product else 'Desconocido'
        
        # Actualizar el lote
        batch = Batch.update(batch_id, data)
        
        # Si se modificó la cantidad, registrar en el historial con detalles completos
        if 'quantity' in data and data['quantity'] != old_batch['quantity']:
            old_quantity = old_batch['quantity']
            new_quantity = data['quantity']
            difference = new_quantity - old_quantity
            
            History.log_action(
                user=user,
                action='stock_change',
                entity_type='batch',
                entity_id=batch_id,
                details={
                    'product_id': old_batch['product_id'],
                    'product_name': product_name,
                    'old_quantity': old_quantity,
                    'new_quantity': new_quantity,
                    'difference': difference,
                    'expiry_date': old_batch.get('expiry_date', '')
                }
            )
        else:
            # Registro normal para otros cambios
            History.log_action(
                user=user,
                action='update',
                entity_type='batch',
                entity_id=batch_id,
                details=data
            )
        
        return jsonify(batch), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/batches/<batch_id>', methods=['DELETE'])
@jwt_required()
def delete_batch(batch_id):
    """Eliminar lote"""
    try:
        user = get_current_user()
        
        Batch.delete(batch_id)
        
        History.log_action(
            user=user,
            action='delete',
            entity_type='batch',
            entity_id=batch_id
        )
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/batches/expiring', methods=['GET'])
@jwt_required()
def get_expiring_batches():
    """Obtener lotes próximos a vencer"""
    try:
        days = request.args.get('days', 30, type=int)
        batches = Batch.get_expiring_soon(days)
        return jsonify(batches), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/stock-history', methods=['GET'])
@jwt_required()
def get_stock_history():
    """Obtener historial de modificaciones de stock"""
    try:
        product_id = request.args.get('product_id')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Construir query para filtrar solo cambios de stock
        query = {
            'action': 'stock_change',
            'entity_type': 'batch'
        }
        
        # Filtrar por producto si se especifica
        if product_id:
            query['details.product_id'] = product_id
        
        # Obtener historial desde MongoDB
        from models import history_collection
        entries = list(
            history_collection.find(query)
            .sort('timestamp', -1)
            .skip(offset)
            .limit(limit)
        )
        
        # Convertir ObjectId a string y formatear
        for entry in entries:
            entry['_id'] = str(entry['_id'])
            # Agregar timestamp en formato ISO para el frontend
            if 'timestamp' in entry:
                entry['timestamp_iso'] = entry['timestamp'].isoformat()
        
        return jsonify(entries), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Rutas para promociones
@products_bp.route('/api/admin/promotions', methods=['GET'])
@jwt_required()
def get_all_promotions():
    """Obtener todas las promociones"""
    try:
        promotions = Promotion.find_all()
        return jsonify(promotions), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/promotions', methods=['POST'])
@jwt_required()
def create_promotion():
    """Crear nueva promoción"""
    try:
        user = get_current_user()
        data = request.json
        
        if not all(key in data for key in ['name', 'type', 'rules']):
            return jsonify({'error': 'Faltan campos requeridos'}), 400
        
        promotion = Promotion.create(data)
        
        History.log_action(
            user=user,
            action='create',
            entity_type='promotion',
            entity_id=promotion['_id'],
            details={'name': promotion['name']}
        )
        
        return jsonify(promotion), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/promotions/<promo_id>', methods=['PUT'])
@jwt_required()
def update_promotion(promo_id):
    """Actualizar promoción"""
    try:
        user = get_current_user()
        data = request.json
        
        promotion = Promotion.update(promo_id, data)
        
        History.log_action(
            user=user,
            action='update',
            entity_type='promotion',
            entity_id=promo_id,
            details={'name': promotion['name']}
        )
        
        return jsonify(promotion), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/promotions/<promo_id>', methods=['DELETE'])
@jwt_required()
def delete_promotion(promo_id):
    """Eliminar promoción"""
    try:
        user = get_current_user()
        
        Promotion.delete(promo_id)
        
        History.log_action(
            user=user,
            action='delete',
            entity_type='promotion',
            entity_id=promo_id
        )
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# RUTAS DE CATEGORÍAS
@products_bp.route('/api/admin/categories', methods=['GET'])
@jwt_required()
def get_categories():
    """Obtener todas las categorías"""
    try:
        from models import Category
        categories = Category.find_all()
        return jsonify(categories), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/categories', methods=['POST'])
@jwt_required()
def create_category():
    """Crear nueva categoría"""
    try:
        from models import Category
        user = get_current_user()
        data = request.json
        
        if not data.get('name'):
            return jsonify({'error': 'Nombre requerido'}), 400
        
        category = Category.create(data['name'])
        
        History.log_action(
            user=user,
            action='create',
            entity_type='category',
            entity_id=category['_id'],
            details={'name': category['name']}
        )
        
        return jsonify(category), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/categories/<category_id>', methods=['PUT'])
@jwt_required()
def update_category(category_id):
    """Actualizar categoría"""
    try:
        from models import Category
        user = get_current_user()
        data = request.json
        
        category = Category.update(category_id, data['name'])
        
        History.log_action(
            user=user,
            action='update',
            entity_type='category',
            entity_id=category_id,
            details={'name': data['name']}
        )
        
        return jsonify(category), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/categories/<category_id>', methods=['DELETE'])
@jwt_required()
def delete_category(category_id):
    """Eliminar categoría"""
    try:
        from models import Category
        user = get_current_user()
        
        Category.delete(category_id)
        
        History.log_action(
            user=user,
            action='delete',
            entity_type='category',
            entity_id=category_id
        )
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# RUTAS DE CONFIGURACIÓN DEL SITIO
@products_bp.route('/api/config', methods=['GET'])
def get_site_config():
    """Obtener configuración del sitio (pública)"""
    try:
        from models import SiteConfig
        config = SiteConfig.get_config()
        return jsonify(config), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/config', methods=['GET'])
@jwt_required()
def get_site_config_admin():
    """Obtener configuración del sitio (admin)"""
    try:
        from models import SiteConfig
        config = SiteConfig.get_config()
        return jsonify(config), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/admin/config', methods=['PUT'])
@jwt_required()
def update_site_config():
    """Actualizar configuración del sitio"""
    try:
        from models import SiteConfig
        user = get_current_user()
        data = request.json
        
        config = SiteConfig.update_config(data)
        
        History.log_action(
            user=user,
            action='update',
            entity_type='config',
            entity_id='catalog',
            details={'message': 'Actualizó configuración del catálogo'}
        )
        
        return jsonify(config), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500