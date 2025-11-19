from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import random
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# SECURITY FIX: Use environment variable for secret key
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# DATABASE FIX: Proper Railway PostgreSQL configuration
database_url = os.environ.get('DATABASE_URL')

if database_url:
    # Fix for Railway/Heroku PostgreSQL URL format
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Fallback for local development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://food_user:Godhasincreasedme700%@localhost/food_ordering'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ✅ FIXED: Single initialization (remove duplicates)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), default='customer')  # customer, kitchen, admin
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

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    delivery_option = db.Column(db.String(20), nullable=False)  # delivery, pickup
    delivery_address = db.Column(db.Text)
    pickup_time = db.Column(db.String(10))
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, preparing, ready, completed, cancelled
    order_time = db.Column(db.DateTime, default=datetime.utcnow)
    expected_ready_time = db.Column(db.String(10))
    special_instructions = db.Column(db.Text)
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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize menu items
def init_menu_items():
    if MenuItem.query.count() == 0:
        menu_items = [
            MenuItem(
                name="Burger", 
                price=9.99, 
                emoji="🍔", 
                color="#FF6B35", 
                category="Main",
                description="Juicy beef patty with fresh lettuce, tomato, and our special sauce"
            ),
            MenuItem(
                name="Pizza", 
                price=15.99, 
                emoji="🍕", 
                color="#F7C59F", 
                category="Main",
                description="Freshly baked with mozzarella, pepperoni, and your choice of toppings"
            ),
            MenuItem(
                name="Pasta", 
                price=11.99, 
                emoji="🍝", 
                color="#EFEFD0", 
                category="Main",
                description="Homemade pasta with rich tomato sauce and parmesan cheese"
            ),
            MenuItem(
                name="Salad", 
                price=8.99, 
                emoji="🥗", 
                color="#A7C957", 
                category="Main",
                description="Fresh garden greens with seasonal vegetables and light dressing"
            ),
            MenuItem(
                name="Soda", 
                price=2.99, 
                emoji="🥤", 
                color="#00A8E8", 
                category="Drink",
                description="Refreshing carbonated beverage, various flavors available"
            ),
            MenuItem(
                name="Fries", 
                price=3.99, 
                emoji="🍟", 
                color="#FF9E00", 
                category="Side",
                description="Crispy golden fries with a pinch of sea salt"
            ),
            MenuItem(
                name="Ice Cream", 
                price=4.99, 
                emoji="🍦", 
                color="#FFE5D9", 
                category="Dessert",
                description="Creamy vanilla ice cream with your choice of toppings"
            ),
            MenuItem(
                name="Tea", 
                price=20.00, 
                emoji="🍵", 
                color="#D4E6B3", 
                category="Drink",
                description="Premium tea selection, brewed to perfection"
            )
        ]
        db.session.bulk_save_objects(menu_items)
        db.session.commit()

# ✅ FIXED: Add missing kitchen user function
def create_kitchen_user():
    if not User.query.filter_by(email='kitchen@example.com').first():
        hashed_password = bcrypt.generate_password_hash('kitchen123').decode('utf-8')
        kitchen_user = User(
            email='kitchen@example.com',
            name='Kitchen Staff',
            phone='254700000000',
            password_hash=hashed_password,
            role='kitchen'
        )
        db.session.add(kitchen_user)
        db.session.commit()
        print("✅ Kitchen user created: kitchen@example.com / kitchen123")

# Routes
@app.route('/')
def index():
    menu_items = MenuItem.query.filter_by(is_available=True).all()
    
    # Calculate cart total if user is authenticated and has items in cart
    cart_total = 0
    if current_user.is_authenticated:
        cart = session.get('cart', {})
        for item_id, quantity in cart.items():
            menu_item = MenuItem.query.get(int(item_id))
            if menu_item:
                cart_total += menu_item.price * quantity
    
    return render_template('index.html', 
                         menu_items=menu_items, 
                         cart_total=cart_total,
                         delivery_fee=2.99)

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
    
    # Verify item exists and is available
    menu_item = MenuItem.query.get(int(item_id))
    if not menu_item or not menu_item.is_available:
        return jsonify({'success': False, 'message': 'Item not available'})
    
    # Update cart
    cart = session.get('cart', {})
    cart[item_id] = cart.get(item_id, 0) + quantity
    session['cart'] = cart
    session.modified = True
    
    return jsonify({
        'success': True, 
        'cart_count': sum(cart.values()),
        'message': f'Added {menu_item.name} to cart'
    })

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    # Calculate cart items and total
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
            cart_items.append({
                'item': menu_item,
                'quantity': quantity,
                'item_total': item_total
            })
            total += item_total
    
    # Add delivery fee if applicable
    delivery_fee = 2.99
    
    if request.method == 'POST':
        delivery_option = request.form.get('delivery_option')
        delivery_address = request.form.get('delivery_address', '')
        pickup_time = request.form.get('pickup_time', '')
        special_instructions = request.form.get('special_instructions', '')
        phone = request.form.get('phone', '')
        
        # Generate order number
        order_number = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"
        
        # Calculate preparation time
        prep_time = random.randint(20, 40) if delivery_option == 'delivery' else random.randint(15, 30)
        expected_ready_time = (datetime.now() + timedelta(minutes=prep_time)).strftime('%H:%M')
        
        # Create order
        order = Order(
            user_id=current_user.id,
            order_number=order_number,
            total_amount=total + (delivery_fee if delivery_option == 'delivery' else 0),
            delivery_option=delivery_option,
            delivery_address=delivery_address,
            pickup_time=pickup_time,
            expected_ready_time=expected_ready_time,
            special_instructions=special_instructions
        )
        db.session.add(order)
        db.session.commit()
        
        # Create order items
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
        
        # Create initial status history
        status_history = OrderStatusHistory(
            order_id=order.id,
            status='pending',
            note='Order received'
        )
        db.session.add(status_history)
        db.session.commit()
        
        # Clear cart
        session.pop('cart', None)
        
        flash(f'Order #{order_number} placed successfully!', 'success')
        return redirect(url_for('order_confirmation', order_id=order.id))
    
    return render_template('checkout.html', 
                         cart_items=cart_items, 
                         total=total,
                         delivery_fee=delivery_fee)

@app.route('/order/<int:order_id>')
@login_required
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Security check - users can only see their own orders unless they're staff
    if order.user_id != current_user.id and current_user.role not in ['kitchen', 'admin']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    return render_template('order_confirmation.html', order=order)

@app.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    session.pop('cart', None)
    return jsonify({'success': True})

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
            cart_items.append({
                'item': menu_item,
                'quantity': quantity,
                'item_total': item_total
            })
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
            # Remove item if quantity becomes 0 or negative
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

# Kitchen Routes
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
    status_history = OrderStatusHistory(
        order_id=order.id,
        status=new_status,
        note=note
    )
    db.session.add(status_history)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Status updated'})

@app.route('/kitchen/analytics')
@login_required
def kitchen_analytics():
    if current_user.role not in ['kitchen', 'admin']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Analytics calculations
    total_orders = Order.query.count()
    pending_orders = Order.query.filter_by(status='pending').count()
    preparing_orders = Order.query.filter_by(status='preparing').count()
    ready_orders = Order.query.filter_by(status='ready').count()
    
    # Today's orders
    today = datetime.now().date()
    today_orders = Order.query.filter(db.func.date(Order.order_time) == today).count()
    
    # Popular items (simplified)
    from sqlalchemy import func
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

# Admin Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    users_count = User.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    return render_template('admin_dashboard.html', users_count=users_count, total_revenue=total_revenue)

# ✅ FIXED: Add production configuration
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_menu_items()
        create_kitchen_user()
    
    # Railway sets the PORT environment variable
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)