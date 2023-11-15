from datetime import datetime
import re
from flask import Flask, flash, render_template, request, redirect, url_for, session
from flask_migrate import Migrate
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from models import CartItem, db,StoreManager, Customer, Product, Category,User
from werkzeug.utils import secure_filename
import os
from sqlalchemy import or_, and_

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///grocery_app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/images'
db.init_app(app)
app.secret_key = 'your-secret-key'

migrate = Migrate(app, db)
admin = Admin(app)
admin.add_view(ModelView(Customer, db.session))
admin.add_view(ModelView(Category, db.session))
admin.add_view(ModelView(Product, db.session))
admin.add_view(ModelView(StoreManager, db.session))
admin.add_view(ModelView(CartItem, db.session))
admin.add_view(ModelView(User, db.session))



USERNAME_PATTERN = r"^[a-zA-Z0-9]+$"
PASSWORD_PATTERN = r"^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"

# A list to store the grocery items
grocery_items = []

# First page - Login
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'user' in request.form:
            return redirect('/customer/login')
        elif 'store_manager' in request.form:
            return redirect('/manager/login')

    return render_template('index.html')

@app.route('/customer/login', methods=['GET', 'POST'])
def customer_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        customer = Customer.query.filter_by(username=username).first()

        if customer and customer.password == password:
            session['customer_id'] = customer.id
            return redirect(url_for('customer_dashboard'))
        else:
            return redirect(url_for('customer_register'))

    return render_template('customer_login.html')

@app.route('/customer/register', methods=['GET', 'POST'])
def customer_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        existing_customer = Customer.query.filter_by(username=username).first()

        if existing_customer:
            flash('Customer already exists.', 'cus_regis')
            return render_template('customer_register.html')
        
        errors={}
        if not re.match(USERNAME_PATTERN, username):
            errors['username'] = 'Username must contain only alphanumeric characters.'

        if not re.match(PASSWORD_PATTERN, password):
            errors['password'] = 'Password must be at least 8 characters long and contain at least one uppercase letter, one number, and one special character.'

        if errors:
            return render_template('customer_register.html', errors=errors)

        new_customer = Customer(username=username, password=password)
        new_user = User(username=username, password=password,is_store_manager=False)
        
        db.session.add(new_customer)
        db.session.add(new_user)
        db.session.commit()
        session['customer_id'] = new_customer.id
        return redirect(url_for('customer_dashboard'))
    return render_template('customer_register.html')

def fetch_cart_items():
    cart_items = CartItem.query.filter_by(user_id=session['customer_id']).all()
    products = []
    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_id)
        if product:
            products.append(Product(id=product.id, name=product.name, price=product.price, stock=cart_item.quantity))
    return products

@app.route('/customer/dashboard', methods=['GET', 'POST'])
def customer_dashboard():
    categories = Category.query.all()
    products = Product.query.all()
    search_results = None
    cart_items = fetch_cart_items()
    total_amount = 0
    for item in cart_items:
        total_amount = total_amount + (item.price * item.stock )
    return render_template('user_dashboard.html', categories=categories, products=products, search_results=search_results,cart_items=cart_items,total_amount=total_amount)

@app.route('/search_products', methods=['GET'])
def search_products():
    query = request.args.get('query')
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    min_date = request.args.get('min_date')
    max_date = request.args.get('max_date')
    search_results=[]
    if query or min_price or max_price or min_date or max_date:
        base_query = Product.query.filter(or_(
            Product.name.ilike(f'%{query}%'),
            Product.category.has(Category.name.ilike(f'%{query}%'))
        ))
        if min_price:
            base_query = base_query.filter(Product.price >= min_price)
        if max_price:
            base_query = base_query.filter(Product.price <= max_price)
        if min_date:
            base_query = base_query.filter(Product.manufacturing_date >= min_date)
        if max_date:
            base_query = base_query.filter(Product.expiry_date <= max_date)

        search_results = base_query.all()
        return render_template('user_dashboard.html', search_results=search_results,val=query, min_price=min_price, max_price=max_price, min_date=min_date, max_date=max_date)
        
    categories = Category.query.all()
    products = Product.query.all()
    return render_template('user_dashboard.html', categories=categories, products=products, search_results="")
    
@app.route('/category_products/<int:category_id>')
def category_products(category_id):
    category = Category.query.get_or_404(category_id)
    products = Product.query.filter_by(category=category).all()
    cart_items = fetch_cart_items()
    total_amount = 0
    for item in cart_items:
        total_amount = total_amount + (item.price * item.stock )
    return render_template('category_products.html', category=category, products=products,cart_items=cart_items,total_amount=total_amount)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    uid = session['customer_id']
    product_id = int(request.form.get('product_id'))
    quantity = int(request.form.get('quantity'))
    
    cart_item = CartItem.query.filter_by(user_id=uid, product_id=product_id).first()
    
    if cart_item:
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(product_id=product_id, quantity=quantity, user_id=uid)
        db.session.add(cart_item)
    
    db.session.commit()
    return redirect(url_for('customer_dashboard'))

@app.route('/clear_cart',methods=['POST','GET'])
def clear_cart():
    cart_items = CartItem.query.filter_by(user_id=session['customer_id']).all()
    for cart_item in cart_items:
        db.session.delete(cart_item)
    db.session.commit()
    return redirect(url_for('customer_dashboard'))

@app.route('/delete_item/',methods=["GET","POST"])
def delete_item():
    uid = session['customer_id']
    product_id = request.form['product_id']
    cart_item = CartItem.query.filter_by(user_id=uid, product_id=product_id).all()
    for item in cart_item:
        db.session.delete(item)
    db.session.commit()
    return redirect(url_for('customer_dashboard'))
    
@app.route('/process_payment', methods=['POST'])
def process_payment():
    uid = session['customer_id']
    total_amt = request.form['total_amount']
    cart_items = CartItem.query.filter_by(user_id=uid).all()

    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_id)
        if product:
            product.stock -= cart_item.quantity
            db.session.add(product)
    
    db.session.commit()
    return render_template("process_payment.html", amount=total_amt)

@app.route('/order_placed', methods = ['GET','POST'])
def order_placed():
    uid = session['customer_id']
    cart_items = CartItem.query.filter_by(user_id=uid).all()
    for cart_item in cart_items:
        db.session.delete(cart_item)
    db.session.commit()
    return render_template('order_placed.html')

@app.route('/manager/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        store_manager = StoreManager.query.filter_by(username=username).first()

        if store_manager and store_manager.password == password:
            session['store_manager_id'] = store_manager.id
            return redirect(url_for("store_manager_dashboard"))
        else:
            flash("Store manager doesn't exist.", 'regis')
            return redirect(url_for('register'))

    return render_template('sm_login.html')

@app.route('/manager/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_store_manager = StoreManager.query.filter_by(username=username).first()

        if existing_store_manager:
            flash('Store manager already exists.', 'login')
            return render_template('sm_login.html')

        # Validate username and password
        errors = {}
        if not re.match(USERNAME_PATTERN, username):
            errors['username'] = 'Username must contain only alphanumeric characters.'

        if not re.match(PASSWORD_PATTERN, password):
            errors['password'] = 'Password must be at least 8 characters long and contain at least one uppercase letter, one number, and one special character.'

        if errors:
            return render_template('sm_register.html', errors=errors)

        new_store_manager = StoreManager(username=username, password=password)
        new_user = User(username=username, password=password,is_store_manager=True)
        
        db.session.add(new_store_manager)
        db.session.add(new_user)
        db.session.commit()

        session['store_manager_id'] = new_store_manager.id
        return render_template('store_manager.html')
    return render_template('sm_register.html')

@app.route('/store_manager/dashboard')
def store_manager_dashboard():
    categories = Category.query.all()
    return render_template('store_manager.html', categories=categories)
 
@app.route('/store_manager/categories', methods=['GET', 'POST'])
def store_manager_categories():
    categories = Category.query.all()
    
    if request.method == 'POST':
        new_category_name = request.form['new_category_name']
        if new_category_name:
            if 'cat_photo' in request.files:
                    cphoto = request.files['cat_photo']
                    if cphoto.filename != '':
                        filename = secure_filename(cphoto.filename)
                        cphoto.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_category = Category(name=new_category_name,cat_photo=filename, store_manager_id=session['store_manager_id'])
            db.session.add(new_category)
            db.session.commit()
            return redirect(url_for('store_manager_categories'))
        else:
            flash('Category name cannot be empty.', 'error')
    
    return render_template('store_manager_categories.html', categories=categories)

@app.route('/store_manager/edit_category/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    category = Category.query.get(category_id)
    
    if category.store_manager_id != session['store_manager_id']:
        flash('You do not have permission to edit this category.', 'error')
        return redirect(url_for('store_manager_categories'))
    
    if request.method == 'POST':
        new_image = request.files['cat_photo']
        category.name = request.form['category_name']
        if new_image:
            if category.cat_photo:
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], category.cat_photo)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            filename = secure_filename(new_image.filename)
            new_image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            category.cat_photo = filename
        db.session.commit()
        return redirect(url_for('store_manager_categories'))
    
    return render_template('edit_category.html', category=category)

@app.route('/store_manager/delete_category/<int:category_id>', methods=['POST'])
def delete_category(category_id):
    category = Category.query.get(category_id)
    items = Product.query.filter_by(category_id = category_id)

    if category.store_manager_id != session['store_manager_id']:
        flash('You do not have permission to delete this category.', 'error')
    else:
        for i in items:
            db.session.delete(i)
        db.session.delete(category)
        db.session.commit()
            
    return redirect(url_for('store_manager_categories'))

@app.route('/store_manager/add_category', methods=['GET','POST'])
def add_category():
    if request.method == 'POST':
        category_name = request.form.get('category_name')

        if not category_name:
            flash('Category name cannot be empty.', 'error')
        else:
            try:
                store_manager_id = session.get('store_manager_id')
                if store_manager_id is None:
                    flash('Store manager information not found. Please log in.', 'error')
                    return redirect(url_for('login'))  

                category = Category(name=category_name, store_manager_id=store_manager_id)
                db.session.add(category)
                db.session.commit()

            except Exception as e:
                db.session.rollback()
                flash('Failed to add category. Please try again later.', 'error')

    return redirect(url_for('store_manager_dashboard'))

@app.route('/store_manager/products')
def store_manager_products():
    categories = Category.query.all()    
    return render_template('store_manager_products.html', categories=categories)

@app.route('/store_manager/add_product', methods=['POST'])
def add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        stock = request.form.get('stock')
        unit = request.form.get('unit')
        manufacturing_date = request.form.get('manufacturing_date')
        expiry_date = request.form.get('expiry_date')
        category_id = request.form.get('category')
       

        if not all([name, price, stock, unit, manufacturing_date, expiry_date, category_id]):
            flash('Please fill all the required fields.', 'error')
        else:
            try:
                price = float(price)
                stock = int(stock)
                manufacturing_date = datetime.strptime(manufacturing_date, '%Y-%m-%d')
                expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d')
                if 'photo' in request.files:
                    photo = request.files['photo']
                    if photo.filename != '':
                        filename = secure_filename(photo.filename)
                        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                new_product = Product(
                    name=name,
                    description=description,
                    price=price,
                    stock=stock,
                    unit=unit,
                    manufacturing_date=manufacturing_date,
                    expiry_date=expiry_date,
                    category_id=category_id,
                    photo = filename
                )
                
                db.session.add(new_product)
                db.session.commit()
                flash('Product added successfully.', 'success')
            except ValueError:
                flash('Invalid input for price or stock, or date format.', 'error')
            except Exception as e:
                db.session.rollback()
                flash('Failed to add product. Please try again later.', 'error')

    return redirect(url_for('store_manager_products'))

@app.route('/store_manager/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    categories = Category.query.all()
    new_image = request.files.get('photo')
    
    if request.method == 'POST':
        if 'name' in request.form:
            product.name = request.form['name']
        if 'description' in request.form:
            product.description = request.form['description']
        if 'price' in request.form:
            product.price = float(request.form['price'])
        if 'stock' in request.form:
            product.stock = int(request.form['stock'])
        if 'unit' in request.form:
            product.unit = request.form['unit']
        if 'manufacturing_date' in request.form:
            manufacturing_date = datetime.strptime(request.form['manufacturing_date'], '%Y-%m-%d').date()
            product.manufacturing_date = manufacturing_date
        if 'expiry_date' in request.form:
            expiry_date = datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date()
            product.expiry_date = expiry_date
        if 'category' in request.form:
            category_id = int(request.form['category'])
            category = Category.query.get(category_id)
            product.category = category
        if new_image:
            if product.photo:
                old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], product.photo)
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            filename = secure_filename(new_image.filename)
            new_image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            product.photo = filename

        db.session.commit()
        flash('Product updated successfully.', 'success')
        return redirect(url_for('store_manager_products'))

    return render_template('edit_product.html', product=product, categories=categories)

@app.route('/store_manager/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    old_filename = product.photo
    if old_filename:
        old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], old_filename)
        if os.path.exists(old_filepath):
            os.remove(old_filepath)

    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully', 'success')
    return redirect(url_for('store_manager_products'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
