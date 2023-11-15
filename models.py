from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    store_manager_id = db.Column(db.Integer, db.ForeignKey('store_manager.id'), nullable=False)
    store_manager = db.relationship('StoreManager', back_populates='categories')
    cat_photo = db.Column(db.String(255),nullable=False)
    products = db.relationship('Product', backref='category', lazy=True)
    
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100),unique=True, nullable=False)
    description = db.Column(db.Text,nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False) 
    unit = db.Column(db.String(10), nullable=False)
    manufacturing_date = db.Column(db.Date,nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    photo = db.Column(db.String(255), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category_ref = db.relationship('Category', backref='products_association')
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    is_store_manager = db.Column(db.Boolean, default=False)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class StoreManager(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    categories = db.relationship('Category', back_populates='store_manager')


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)