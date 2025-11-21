from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import random
import os
from dotenv import load_dotenv
from sqlalchemy import func
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from sqlalchemy import text

load_dotenv()

app = Flask(__name__)

# Configuration
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'MyGodisgreat:Jesusreigns')

# Database configuration
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Fix common PostgreSQL URL issue (Heroku etc.)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Fallback to local development database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://food_user:Godhasincreasedme700%@localhost/food_ordering'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Database Models (Include all your models here)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='customer')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='customer', lazy=True)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    emoji = db.Column(db.String(10))
    color = db.Column(db.String(20))
    is_available = db.Column(db.Boolean, default=True)
    order_items = db.relationship('OrderItem', backref='menu_item', lazy=True)
    total_sold = db.Column(db.Integer, default=0)
    total_revenue = db.Column(db.Float, default=0.0)
    cost_per_plate = db.Column(db.Float, default=0.0)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    delivery_option = db.Column(db.String(20), nullable=False)
    delivery_address = db.Column(db.Text)
    pickup_time = db.Column(db.String(10))
    status = db.Column(db.String(20), default='pending')
    order_time = db.Column(db.DateTime, default=datetime.utcnow)
    expected_ready_time = db.Column(db.String(10))
    special_instructions = db.Column(db.Text)
    payment_status = db.Column(db.String(20), default='pending')
    order_items = db.relationship('OrderItem', backref='order', lazy=True)
    status_history = db.relationship('OrderStatusHistory', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    menu_item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    item_total = db.Column(db.Float, nullable=False)

class OrderStatusHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    note = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    current_stock = db.Column(db.Float, default=0.0)
    cost_per_unit = db.Column(db.Float, nullable=False)
    reorder_level = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ingredient_usage = db.relationship('IngredientUsage', backref='ingredient', lazy=True)
    stock_history = db.relationship('StockHistory', backref='ingredient', lazy=True)

class IngredientUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=False)
    quantity_used = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StockHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=False)
    change_type = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    note = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialization functions
def init_menu_items():
    if MenuItem.query.count() == 0:
        menu_items = [
            MenuItem(name="Burger", price=9.99, emoji="🍔", color="#FF6B35", category="Main", description="Juicy beef patty with fresh lettuce, tomato, and our special sauce"),
            MenuItem(name="Pizza", price=15.99, emoji="🍕", color="#F7C59F", category="Main", description="Freshly baked with mozzarella, pepperoni, and your choice of toppings"),
            MenuItem(name="Pasta", price=11.99, emoji="🍝", color="#EFEFD0", category="Main", description="Homemade pasta with rich tomato sauce and parmesan cheese"),
            MenuItem(name="Salad", price=8.99, emoji="🥗", color="#A7C957", category="Main", description="Fresh garden greens with seasonal vegetables and light dressing"),
            MenuItem(name="Soda", price=2.99, emoji="🥤", color="#00A8E8", category="Drink", description="Refreshing carbonated beverage, various flavors available"),
            MenuItem(name="Fries", price=3.99, emoji="🍟", color="#FF9E00", category="Side", description="Crispy golden fries with a pinch of sea salt"),
            MenuItem(name="Ice Cream", price=4.99, emoji="🍦", color="#FFE5D9", category="Dessert", description="Creamy vanilla ice cream with your choice of toppings"),
            MenuItem(name="Tea", price=20.00, emoji="🍵", color="#D4E6B3", category="Drink", description="Premium tea selection, brewed to perfection")
        ]
        db.session.bulk_save_objects(menu_items)
        db.session.commit()

def init_ingredients():
    if Ingredient.query.count() == 0:
        ingredients = [
            Ingredient(name="Beef Patty", unit="pieces", cost_per_unit=2.50, current_stock=100),
            Ingredient(name="Burger Bun", unit="pieces", cost_per_unit=0.50, current_stock=200),
            Ingredient(name="Lettuce", unit="kg", cost_per_unit=3.00, current_stock=10),
            Ingredient(name="Tomato", unit="kg", cost_per_unit=2.00, current_stock=8),
            Ingredient(name="Cheese", unit="kg", cost_per_unit=8.00, current_stock=5),
            Ingredient(name="Tea Leaves", unit="kg", cost_per_unit=15.00, current_stock=5),
            Ingredient(name="Sugar", unit="kg", cost_per_unit=1.50, current_stock=20),
            Ingredient(name="Milk", unit="liters", cost_per_unit=1.20, current_stock=15),
        ]
        db.session.bulk_save_objects(ingredients)
        db.session.commit()

def init_ingredient_usage():
    if IngredientUsage.query.count() == 0:
        burger = MenuItem.query.filter_by(name="Burger").first()
        tea = MenuItem.query.filter_by(name="Tea").first()
        if burger and tea:
            usage = [
                IngredientUsage(menu_item_id=burger.id, ingredient_id=1, quantity_used=1),
                IngredientUsage(menu_item_id=burger.id, ingredient_id=2, quantity_used=1),
                IngredientUsage(menu_item_id=burger.id, ingredient_id=3, quantity_used=0.05),
                IngredientUsage(menu_item_id=burger.id, ingredient_id=4, quantity_used=0.08),
                IngredientUsage(menu_item_id=burger.id, ingredient_id=5, quantity_used=0.03),
                IngredientUsage(menu_item_id=tea.id, ingredient_id=6, quantity_used=0.01),
                IngredientUsage(menu_item_id=tea.id, ingredient_id=7, quantity_used=0.015),
                IngredientUsage(menu_item_id=tea.id, ingredient_id=8, quantity_used=0.2),
            ]
            db.session.bulk_save_objects(usage)
            db.session.commit()
            calculate_menu_item_costs()

def calculate_menu_item_costs():
    menu_items = MenuItem.query.all()
    for item in menu_items:
        total_cost = 0.0
        usages = IngredientUsage.query.filter_by(menu_item_id=item.id).all()
        for usage in usages:
            ingredient = Ingredient.query.get(usage.ingredient_id)
            if ingredient:
                total_cost += usage.quantity_used * ingredient.cost_per_unit
        item.cost_per_plate = total_cost
    db.session.commit()

def create_kitchen_user():
    if not User.query.filter_by(email='kitchen@example.com').first():
        hashed_password = bcrypt.generate_password_hash('kitchen123').decode('utf-8')
        kitchen_user = User(email='kitchen@example.com', name='Kitchen Staff', phone='254700000000', password_hash=hashed_password, role='kitchen')
        db.session.add(kitchen_user)
        db.session.commit()

def create_admin_user():
    if not User.query.filter_by(email='admin@example.com').first():
        hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
        admin_user = User(email='admin@example.com', name='Administrator', phone='254700000001', password_hash=hashed_password, role='admin')
        db.session.add(admin_user)
        db.session.commit()

def update_sales_and_inventory(order):
    for order_item in order.order_items:
        menu_item = MenuItem.query.get(order_item.menu_item_id)
        if menu_item:
            menu_item.total_sold += order_item.quantity
            menu_item.total_revenue += order_item.item_total
            usages = IngredientUsage.query.filter_by(menu_item_id=menu_item.id).all()
            for usage in usages:
                ingredient = Ingredient.query.get(usage.ingredient_id)
                if ingredient:
                    total_used = usage.quantity_used * order_item.quantity
                    ingredient.current_stock -= total_used
                    stock_history = StockHistory(
                        ingredient_id=ingredient.id,
                        change_type='usage',
                        quantity=-total_used,
                        note=f'Used for {order_item.quantity} x {menu_item.name} (Order: {order.order_number})'
                    )
                    db.session.add(stock_history)
    db.session.commit()

# ... your database models code ...

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== FIX: DATABASE INITIALIZATION ====================

def initialize_database():
    """Initialize database tables and data"""
    with app.app_context():
        try:
            print("🚀 Starting database initialization...")
            
            # Create all tables
            db.create_all()
            print("✅ Database tables created")
            
            # Initialize data only if tables are empty
            if MenuItem.query.count() == 0:
                print("📝 Initializing menu items...")
                init_menu_items()
            
            if Ingredient.query.count() == 0:
                print("🥬 Initializing ingredients...")
                init_ingredients()
            
            if IngredientUsage.query.count() == 0:
                print("🔗 Initializing ingredient usage...")
                init_ingredient_usage()
            
            if not User.query.filter_by(email='kitchen@example.com').first():
                print("👨‍🍳 Creating kitchen user...")
                create_kitchen_user()
            
            if not User.query.filter_by(email='admin@example.com').first():
                print("👨‍💼 Creating admin user...")
                create_admin_user()
                
            print("🎉 Database initialization completed!")
            
        except Exception as e:
            print(f"❌ Database error: {str(e)}")
            import traceback
            print(f"🔍 Full traceback: {traceback.format_exc()}")

# Initialize database immediately
print("🔄 Starting database setup...")
initialize_database()
print("✅ Database setup complete")

# Flask-Admin to use a different path for CRUD operations
admin = Admin(app, name='Database Admin', url='/database-admin')

# Simple table viewer without auto-discovery first
@app.route('/admin/tables')
def show_tables():
    try:
        result = db.session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = [row[0] for row in result]
        return {'tables': tables}
    except Exception as e:
        return {'error': str(e)}

# ==================== ROUTES ====================
@app.route('/init')
def init_route():
    """Manual initialization route"""
    try:
        initialize_database()
        return """
        <h1>Database Initialized!</h1>
        <p>Tables created and data populated.</p>
        <p><a href="/">Go to homepage</a></p>
        """
    except Exception as e:
        return f"<h1>Initialization Failed</h1><pre>{str(e)}</pre>"

@app.route('/health')
def health():
    """Health check route"""
    try:
        # Test database connection
        db.engine.connect()
        menu_count = MenuItem.query.count()
        return f"✅ App is healthy! Database connected. Menu items: {menu_count}"
    except Exception as e:
        return f"❌ Health check failed: {str(e)}"

@app.route('/debug-tables')
def debug_tables():
    try:
        from sqlalchemy import text
        result = db.session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = [row[0] for row in result]
        print("=== DATABASE TABLES ===")
        for table in tables:
            print(f"  - {table}")
        print("=======================")
        return {
            'success': True, 
            'tables': tables,
            'message': 'Check Render logs for table list'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ==================== ROUTES ====================

@app.route('/')
def index():
    menu_items = MenuItem.query.filter_by(is_available=True).all()
    cart_total = 0
    if current_user.is_authenticated:
        cart = session.get('cart', {})
        for item_id, quantity in cart.items():
            menu_item = MenuItem.query.get(int(item_id))
            if menu_item:
                cart_total += menu_item.price * quantity
    return render_template('index.html', menu_items=menu_items, cart_total=cart_total, delivery_fee=2.99)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        phone = request.form.get('phone')
        password = request.form.get('password')
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(email=email, name=name, phone=phone, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login failed. Check email and password.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    item_id = str(request.json['item_id'])
    quantity = request.json.get('quantity', 1)
    menu_item = MenuItem.query.get(int(item_id))
    if not menu_item or not menu_item.is_available:
        return jsonify({'success': False, 'message': 'Item not available'})
    cart = session.get('cart', {})
    cart[item_id] = cart.get(item_id, 0) + quantity
    session['cart'] = cart
    session.modified = True
    return jsonify({'success': True, 'cart_count': sum(cart.values()), 'message': f'Added {menu_item.name} to cart'})

@app.route('/cart')
@login_required
def view_cart():
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    for item_id, quantity in cart.items():
        menu_item = MenuItem.query.get(int(item_id))
        if menu_item:
            item_total = menu_item.price * quantity
            cart_items.append({'item': menu_item, 'quantity': quantity, 'item_total': item_total})
            total += item_total
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/update_cart_quantity', methods=['POST'])
@login_required
def update_cart_quantity():
    item_id = str(request.json['item_id'])
    change = request.json['change']
    cart = session.get('cart', {})
    if item_id in cart:
        new_quantity = cart[item_id] + change
        if new_quantity <= 0:
            del cart[item_id]
            removed = True
        else:
            cart[item_id] = new_quantity
            removed = False
        session['cart'] = cart
        session.modified = True
        return jsonify({'success': True, 'removed': removed})
    return jsonify({'success': False, 'message': 'Item not in cart'})

@app.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    item_id = str(request.json['item_id'])
    cart = session.get('cart', {})
    if item_id in cart:
        del cart[item_id]
        session['cart'] = cart
        session.modified = True
    return jsonify({'success': True})

@app.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    session.pop('cart', None)
    return jsonify({'success': True})

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('index'))
    cart_items = []
    total = 0
    for item_id, quantity in cart.items():
        menu_item = MenuItem.query.get(int(item_id))
        if menu_item:
            item_total = menu_item.price * quantity
            cart_items.append({'item': menu_item, 'quantity': quantity, 'item_total': item_total})
            total += item_total
    delivery_fee = 2.99
    if request.method == 'POST':
        delivery_option = request.form.get('delivery_option')
        delivery_address = request.form.get('delivery_address', '')
        pickup_time = request.form.get('pickup_time', '')
        special_instructions = request.form.get('special_instructions', '')
        phone = request.form.get('phone', '')
        order_number = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"
        prep_time = random.randint(20, 40) if delivery_option == 'delivery' else random.randint(15, 30)
        expected_ready_time = (datetime.now() + timedelta(minutes=prep_time)).strftime('%H:%M')
        order = Order(
            user_id=current_user.id,
            order_number=order_number,
            total_amount=total + (delivery_fee if delivery_option == 'delivery' else 0),
            delivery_option=delivery_option,
            delivery_address=delivery_address,
            pickup_time=pickup_time,
            expected_ready_time=expected_ready_time,
            special_instructions=special_instructions,
            payment_status='completed'
        )
        db.session.add(order)
        db.session.commit()
        for item_data in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item_data['item'].id,
                menu_item_name=item_data['item'].name,
                quantity=item_data['quantity'],
                unit_price=item_data['item'].price,
                item_total=item_data['item_total']
            )
            db.session.add(order_item)
        status_history = OrderStatusHistory(
            order_id=order.id,
            status='pending',
            note='Order received and payment completed'
        )
        db.session.add(status_history)
        db.session.commit()
        update_sales_and_inventory(order)
        session.pop('cart', None)
        flash(f'Order #{order_number} placed successfully!', 'success')
        return redirect(url_for('order_confirmation', order_id=order.id))
    return render_template('checkout.html', cart_items=cart_items, total=total, delivery_fee=delivery_fee)

@app.route('/order/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and current_user.role not in ['kitchen', 'admin']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    if order.status == 'completed' and order.payment_status == 'completed':
        update_sales_and_inventory(order)
    return render_template('order_confirmation.html', order=order)

@app.route('/kitchen')
@login_required
def kitchen_dashboard():
    if current_user.role not in ['kitchen', 'admin']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    orders = Order.query.filter(Order.status.in_(['pending', 'confirmed', 'preparing'])).order_by(Order.order_time.desc()).all()
    return render_template('kitchen.html', orders=orders)

@app.route('/kitchen/order/<int:order_id>')
@login_required
def kitchen_order_detail(order_id):
    if current_user.role not in ['kitchen', 'admin']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    order = Order.query.get_or_404(order_id)
    return render_template('kitchen_order_detail.html', order=order)

@app.route('/api/update_order_status', methods=['POST'])
@login_required
def update_order_status():
    if current_user.role not in ['kitchen', 'admin']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    order_id = request.json.get('order_id')
    new_status = request.json.get('status')
    note = request.json.get('note', '')
    order = Order.query.get(order_id)
    if not order:
        return jsonify({'success': False, 'message': 'Order not found'}), 404
    order.status = new_status
    status_history = OrderStatusHistory(order_id=order.id, status=new_status, note=note)
    db.session.add(status_history)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Status updated'})

@app.route('/kitchen/analytics')
@login_required
def kitchen_analytics():
    if current_user.role not in ['kitchen', 'admin']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    preparing_orders = Order.query.filter_by(status='preparing').count()
    ready_orders = Order.query.filter_by(status='ready').count()
    today = datetime.now().date()
    today_orders = Order.query.filter(db.func.date(Order.order_time) == today).count()
    popular_items = db.session.query(
        OrderItem.menu_item_name,
        func.sum(OrderItem.quantity).label('total_quantity')
    ).group_by(OrderItem.menu_item_name).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
    return render_template('kitchen_analytics.html',
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         preparing_orders=preparing_orders,
                         ready_orders=ready_orders,
                         today_orders=today_orders,
                         popular_items=popular_items)

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    users_count = User.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    return render_template('admin_dashboard.html', users_count=users_count, total_revenue=total_revenue)

@app.route('/admin/return-on-plate')
@login_required
def return_on_plate():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    menu_items = MenuItem.query.all()
    roi_data = []
    for item in menu_items:
        if item.cost_per_plate > 0:
            profit_per_plate = item.price - item.cost_per_plate
            roi_percentage = (profit_per_plate / item.cost_per_plate) * 100
        else:
            profit_per_plate = item.price
            roi_percentage = 0
        roi_data.append({
            'item': item,
            'profit_per_plate': profit_per_plate,
            'roi_percentage': roi_percentage,
            'total_profit': profit_per_plate * item.total_sold,
            'total_revenue': item.total_revenue
        })
    roi_data.sort(key=lambda x: x['roi_percentage'], reverse=True)
    total_revenue = sum(item['total_revenue'] for item in roi_data)
    total_cost = sum(item['item'].cost_per_plate * item['item'].total_sold for item in roi_data)
    total_profit = total_revenue - total_cost
    overall_roi = (total_profit / total_cost * 100) if total_cost > 0 else 0
    return render_template('return_on_plate.html',
                         roi_data=roi_data,
                         total_revenue=total_revenue,
                         total_cost=total_cost,
                         total_profit=total_profit,
                         overall_roi=overall_roi)

@app.route('/admin/inventory')
@login_required
def inventory_management():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    ingredients = Ingredient.query.all()
    low_stock = [ing for ing in ingredients if ing.current_stock <= ing.reorder_level]
    return render_template('inventory.html', ingredients=ingredients, low_stock=low_stock)

@app.route('/admin/update-stock', methods=['POST'])
@login_required
def update_stock():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    ingredient_id = request.json.get('ingredient_id')
    quantity = request.json.get('quantity')
    note = request.json.get('note', '')
    ingredient = Ingredient.query.get(ingredient_id)
    if not ingredient:
        return jsonify({'success': False, 'message': 'Ingredient not found'}), 404
    old_stock = ingredient.current_stock
    ingredient.current_stock += quantity
    stock_history = StockHistory(
        ingredient_id=ingredient.id,
        change_type='purchase' if quantity > 0 else 'adjustment',
        quantity=quantity,
        note=note or f'Stock updated from {old_stock} to {ingredient.current_stock}'
    )
    db.session.add(stock_history)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Stock updated successfully'})

@app.route('/admin/ingredient-usage/<int:menu_item_id>')
@login_required
def ingredient_usage(menu_item_id):
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    menu_item = MenuItem.query.get_or_404(menu_item_id)
    usages = IngredientUsage.query.filter_by(menu_item_id=menu_item_id).all()
    usage_data = []
    total_cost = 0.0
    for usage in usages:
        ingredient = Ingredient.query.get(usage.ingredient_id)
        if ingredient:
            cost_for_plate = usage.quantity_used * ingredient.cost_per_unit
            total_cost += cost_for_plate
            usage_data.append({
                'ingredient': ingredient,
                'quantity_used': usage.quantity_used,
                'cost_for_plate': cost_for_plate
            })
    return render_template('ingredient_usage.html',
                         menu_item=menu_item,
                         usage_data=usage_data,
                         total_cost=total_cost)

if __name__ == '__main__':
    # Database is already initialized above
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Flask app on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)

