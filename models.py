from pymongo import MongoClient
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

# Conexión a MongoDB
client = MongoClient(os.getenv('MONGODB_URI'))
db = client['ambar_aromatizantes']

# Colecciones
products_collection = db['products']
batches_collection = db['batches']
users_collection = db['users']
analytics_collection = db['analytics']
history_collection = db['history']
promotions_collection = db['promotions']  # NUEVA

class Product:
    @staticmethod
    def create(data):
        """Crear nuevo producto"""
        product = {
            'name': data['name'],
            'category': data['category'],
            'price': data['price'],
            'images': data.get('images', [data.get('image', '')]),  # Array de imágenes
            'visible': data.get('visible', True),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        result = products_collection.insert_one(product)
        product['_id'] = str(result.inserted_id)
        return product
    
    @staticmethod
    def find_all(visible_only=False):
        """Obtener todos los productos"""
        query = {'visible': True} if visible_only else {}
        products = list(products_collection.find(query))
        for product in products:
            product['_id'] = str(product['_id'])
            # Compatibilidad con productos viejos que tienen 'image'
            if 'images' not in product and 'image' in product:
                product['images'] = [product['image']]
        return products
    
    @staticmethod
    def find_by_id(product_id):
        """Buscar producto por ID"""
        from bson.objectid import ObjectId
        product = products_collection.find_one({'_id': ObjectId(product_id)})
        if product:
            product['_id'] = str(product['_id'])
            # Compatibilidad
            if 'images' not in product and 'image' in product:
                product['images'] = [product['image']]
        return product
    
    @staticmethod
    def update(product_id, data):
        """Actualizar producto"""
        from bson.objectid import ObjectId
        data['updated_at'] = datetime.utcnow()
        products_collection.update_one(
            {'_id': ObjectId(product_id)},
            {'$set': data}
        )
        return Product.find_by_id(product_id)
    
    @staticmethod
    def delete(product_id):
        """Eliminar producto y sus lotes"""
        from bson.objectid import ObjectId
        batches_collection.delete_many({'product_id': product_id})
        result = products_collection.delete_one({'_id': ObjectId(product_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def get_total_stock(product_id):
        """Obtener stock total de un producto"""
        batches = Batch.find_by_product(product_id)
        return sum(batch['quantity'] for batch in batches)

class Batch:
    @staticmethod
    def create(data):
        """Crear nuevo lote"""
        batch = {
            'product_id': data['product_id'],
            'quantity': data['quantity'],
            'expiry_date': data['expiry_date'],
            'notes': data.get('notes', ''),
            'created_at': datetime.utcnow()
        }
        result = batches_collection.insert_one(batch)
        batch['_id'] = str(result.inserted_id)
        return batch
    
    @staticmethod
    def find_by_product(product_id):
        """Obtener todos los lotes de un producto"""
        batches = list(batches_collection.find({'product_id': product_id}).sort('expiry_date', 1))
        for batch in batches:
            batch['_id'] = str(batch['_id'])
        return batches
    
    @staticmethod
    def find_by_id(batch_id):
        """Buscar lote por ID"""
        from bson.objectid import ObjectId
        batch = batches_collection.find_one({'_id': ObjectId(batch_id)})
        if batch:
            batch['_id'] = str(batch['_id'])
        return batch
    
    @staticmethod
    def update(batch_id, data):
        """Actualizar lote"""
        from bson.objectid import ObjectId
        batches_collection.update_one(
            {'_id': ObjectId(batch_id)},
            {'$set': data}
        )
        return Batch.find_by_id(batch_id)
    
    @staticmethod
    def delete(batch_id):
        """Eliminar lote"""
        from bson.objectid import ObjectId
        result = batches_collection.delete_one({'_id': ObjectId(batch_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def get_expiring_soon(days=30):
        """Obtener lotes que vencen pronto"""
        cutoff_date = (datetime.utcnow() + timedelta(days=days)).strftime('%Y-%m-%d')
        batches = list(batches_collection.find({
            'expiry_date': {'$lte': cutoff_date},
            'quantity': {'$gt': 0}
        }).sort('expiry_date', 1))
        
        result = []
        for batch in batches:
            batch['_id'] = str(batch['_id'])
            product = Product.find_by_id(batch['product_id'])
            if product:
                batch['product_name'] = product['name']
            result.append(batch)
        
        return result

class User:
    @staticmethod
    def create(username, password_hash, role='admin'):
        """Crear nuevo usuario"""
        user = {
            'username': username,
            'password': password_hash,
            'role': role,
            'created_at': datetime.utcnow()
        }
        result = users_collection.insert_one(user)
        user['_id'] = str(result.inserted_id)
        return user
    
    @staticmethod
    def find_by_username(username):
        """Buscar usuario por username"""
        user = users_collection.find_one({'username': username})
        if user:
            user['_id'] = str(user['_id'])
        return user
    
    @staticmethod
    def update_password(username, new_password_hash):
        """Actualizar contraseña"""
        users_collection.update_one(
            {'username': username},
            {'$set': {'password': new_password_hash}}
        )

class Analytics:
    @staticmethod
    def log_visit():
        """Registrar visita al catálogo"""
        analytics_collection.update_one(
            {'type': 'visits'},
            {
                '$inc': {'count': 1},
                '$set': {'last_visit': datetime.utcnow()}
            },
            upsert=True
        )
    
    @staticmethod
    def log_product_view(product_id, product_name):
        """Registrar vista de producto"""
        analytics_collection.update_one(
            {'type': 'product_views', 'product_id': product_id},
            {
                '$inc': {'count': 1},
                '$set': {
                    'product_name': product_name,
                    'last_viewed': datetime.utcnow()
                }
            },
            upsert=True
        )
    
    @staticmethod
    def log_add_to_cart(product_id, product_name):
        """Registrar cuando se agrega al carrito (NUEVO)"""
        analytics_collection.update_one(
            {'type': 'cart_adds', 'product_id': product_id},
            {
                '$inc': {'count': 1},
                '$set': {
                    'product_name': product_name,
                    'last_added': datetime.utcnow()
                }
            },
            upsert=True
        )
    
    @staticmethod
    def get_stats():
        """Obtener estadísticas"""
        visits = analytics_collection.find_one({'type': 'visits'})
        product_views = list(analytics_collection.find({'type': 'product_views'}).sort('count', -1).limit(10))
        cart_adds = list(analytics_collection.find({'type': 'cart_adds'}).sort('count', -1).limit(10))
        
        return {
            'total_visits': visits['count'] if visits else 0,
            'top_viewed': [
                {
                    'product_id': pv['product_id'],
                    'product_name': pv['product_name'],
                    'views': pv['count']
                }
                for pv in product_views
            ],
            'top_cart_adds': [
                {
                    'product_id': ca['product_id'],
                    'product_name': ca['product_name'],
                    'cart_adds': ca['count']
                }
                for ca in cart_adds
            ]
        }

class Promotion:
    @staticmethod
    def create(data):
        """Crear nueva promoción"""
        promotion = {
            'name': data['name'],
            'description': data['description'],
            'type': data['type'],  # 'nxm', 'quantity_discount', 'category_deal', 'percentage'
            'rules': data['rules'],  # JSON con reglas específicas
            'applicable_products': data.get('applicable_products', 'all'),  # 'all' o lista de IDs
            'product_ids': data.get('product_ids', []),  # Lista de IDs si no es 'all'
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
            'active': data.get('active', True),
            'combinable': data.get('combinable', False),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        result = promotions_collection.insert_one(promotion)
        promotion['_id'] = str(result.inserted_id)
        return promotion
    
    @staticmethod
    def find_all():
        """Obtener todas las promociones"""
        promos = list(promotions_collection.find().sort('created_at', -1))
        for promo in promos:
            promo['_id'] = str(promo['_id'])
        return promos
    
    @staticmethod
    def find_active():
        """Obtener promociones activas"""
        now = datetime.utcnow().strftime('%Y-%m-%d')
        
        query = {'active': True}
        
        promos = list(promotions_collection.find(query))
        active = []
        
        for promo in promos:
            promo['_id'] = str(promo['_id'])
            
            valid = True
            if promo.get('start_date') and promo['start_date'] > now:
                valid = False
            if promo.get('end_date') and promo['end_date'] < now:
                valid = False
            
            if valid:
                active.append(promo)
        
        return active
    
    @staticmethod
    def find_by_id(promo_id):
        """Buscar promoción por ID"""
        from bson.objectid import ObjectId
        promo = promotions_collection.find_one({'_id': ObjectId(promo_id)})
        if promo:
            promo['_id'] = str(promo['_id'])
        return promo
    
    @staticmethod
    def update(promo_id, data):
        """Actualizar promoción"""
        from bson.objectid import ObjectId
        data['updated_at'] = datetime.utcnow()
        promotions_collection.update_one(
            {'_id': ObjectId(promo_id)},
            {'$set': data}
        )
        return Promotion.find_by_id(promo_id)
    
    @staticmethod
    def delete(promo_id):
        """Eliminar promoción"""
        from bson.objectid import ObjectId
        result = promotions_collection.delete_one({'_id': ObjectId(promo_id)})
        return result.deleted_count > 0

# NUEVO: Modelo de Categorías
class Category:
    @staticmethod
    def create(name):
        """Crear nueva categoría"""
        category = {
            'name': name,
            'created_at': datetime.utcnow()
        }
        result = db['categories'].insert_one(category)
        category['_id'] = str(result.inserted_id)
        return category
    
    @staticmethod
    def find_all():
        """Obtener todas las categorías"""
        categories = list(db['categories'].find().sort('name', 1))
        for cat in categories:
            cat['_id'] = str(cat['_id'])
        return categories
    
    @staticmethod
    def delete(category_id):
        """Eliminar categoría"""
        from bson.objectid import ObjectId
        result = db['categories'].delete_one({'_id': ObjectId(category_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def update(category_id, name):
        """Actualizar categoría"""
        from bson.objectid import ObjectId
        db['categories'].update_one(
            {'_id': ObjectId(category_id)},
            {'$set': {'name': name}}
        )
        cat = db['categories'].find_one({'_id': ObjectId(category_id)})
        if cat:
            cat['_id'] = str(cat['_id'])
        return cat

class History:
    @staticmethod
    def log_action(user, action, entity_type, entity_id, details=None):
        """Registrar acción en historial"""
        entry = {
            'user': user,
            'action': action,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'details': details,
            'timestamp': datetime.utcnow()
        }
        history_collection.insert_one(entry)
    
    @staticmethod
    def get_recent(limit=50):
        """Obtener historial reciente"""
        entries = list(history_collection.find().sort('timestamp', -1).limit(limit))
        for entry in entries:
            entry['_id'] = str(entry['_id'])
        return entries

# NUEVO: Modelo de ConfiguraciÃ³n del Sitio
class SiteConfig:
    @staticmethod
    def get_config():
        """Obtener configuración del sitio"""
        config = db['site_config'].find_one({'type': 'catalog'})
        if not config:
            # Valores por defecto
            config = {
                'type': 'catalog',
                'colors': {
                    'primary': '#9333EA',
                    'secondary': '#EC4899',
                    'accent': '#8B5CF6',
                    'button': '#10B981'
                },
                'contact': {
                    'business_name': 'Ambar Aromatizantes',
                    'whatsapp': '5491170961644',
                    'email': 'contacto@ambar.com',
                    'address': '',
                    'hours': ''
                },
                'social': {
                    'instagram': '',
                    'facebook': '',
                    'tiktok': ''
                },
                'texts': {
                    'title': '✨ Ambar Aromatizantes ✨',
                    'subtitle': 'Descubrí nuestros aromas exclusivos',
                    'promo_message': ''
                },
                'logo_url': '',
                'updated_at': datetime.utcnow()
            }
            db['site_config'].insert_one(config)
        
        if '_id' in config:
            config['_id'] = str(config['_id'])
        return config
    
    @staticmethod
    def update_config(data):
        """Actualizar configuración"""
        data['updated_at'] = datetime.utcnow()
        db['site_config'].update_one(
            {'type': 'catalog'},
            {'$set': data},
            upsert=True
        )
        return SiteConfig.get_config()