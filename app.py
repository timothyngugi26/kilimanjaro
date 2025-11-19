from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import random
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Your existing menu data
MENU = {
    "Burger": 9.99,
    "Pizza": 15.99,
    "Pasta": 11.99,
    "Salad": 8.99,
    "Soda": 2.99,
    "Fries": 3.99,
    "Ice Cream": 4.99,
    "tea": 20.00
}

ITEM_EMOJIS = {
    "Burger": "🍔",
    "Pizza": "🍕", 
    "Pasta": "🍝",
    "Salad": "🥗",
    "Soda": "🥤",
    "Fries": "🍟",
    "Ice Cream": "🍦",
    "tea": "🍵"
}

ITEM_COLORS = {
    "Burger": "#FF6B35",
    "Pizza": "#F7C59F", 
    "Pasta": "#EFEFD0",
    "Salad": "#A7C957",
    "Soda": "#00A8E8",
    "Fries": "#FF9E00",
    "Ice Cream": "#FFE5D9",
    "tea": "#D4E6B3"
}

# Order status constants
ORDER_STATUS = {
    'pending': '🟡 Pending',
    'preparing': '👨‍🍳 Preparing', 
    'ready': '✅ Ready',
    'completed': '📦 Completed',
    'cancelled': '❌ Cancelled'
}

# File to store orders
ORDERS_FILE = 'orders.json'

def load_orders():
    """Load orders from JSON file"""
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_orders(orders):
    """Save orders to JSON file"""
    with open(ORDERS_FILE, 'w') as f:
        json.dump(orders, f, indent=2)

def generate_order_id():
    """Generate a unique order ID"""
    return datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(100, 999))

@app.route('/')
def index():
    if 'order' not in session:
        session['order'] = {}
    if 'total' not in session:
        session['total'] = 0.0
    
    return render_template('index.html', 
                         menu=MENU, 
                         emojis=ITEM_EMOJIS,
                         colors=ITEM_COLORS,
                         order=session['order'],
                         total=session['total'])

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    item = request.json['item']
    price = MENU[item]
    
    if item in session['order']:
        session['order'][item] += 1
    else:
        session['order'][item] = 1
    
    session['total'] += price
    session.modified = True
    
    return jsonify({
        'success': True,
        'order': session['order'],
        'total': session['total']
    })

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    item = request.json['item']
    
    if item in session['order']:
        price = MENU[item]
        session['total'] -= price
        
        if session['order'][item] > 1:
            session['order'][item] -= 1
        else:
            del session['order'][item]
        
        session.modified = True
    
    return jsonify({
        'success': True,
        'order': session['order'],
        'total': session['total']
    })

@app.route('/clear_cart')
def clear_cart():
    session['order'] = {}
    session['total'] = 0.0
    session.modified = True
    return redirect(url_for('index'))

@app.route('/checkout')
def checkout():
    if not session['order']:
        return redirect(url_for('index'))
    
    return render_template('checkout.html', 
                         order=session['order'],
                         total=session['total'],
                         menu=MENU,
                         emojis=ITEM_EMOJIS)

@app.route('/process_checkout', methods=['POST'])
def process_checkout():
    delivery_option = request.form.get('delivery_option')
    location = request.form.get('location', '')
    pickup_time = request.form.get('pickup_time', '')
    phone = request.form.get('phone', '')
    customer_name = request.form.get('customer_name', 'Customer')
    
    # Generate order data
    order_id = generate_order_id()
    order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Calculate preparation time
    if delivery_option == 'delivery':
        prep_time = random.randint(15, 30)
        delivery_info = f"Delivery to: {location}"
    else:
        prep_time = random.randint(10, 20)
        delivery_info = f"Pickup time: {pickup_time}"
    
    ready_time = datetime.now() + timedelta(minutes=prep_time)
    ready_time_str = ready_time.strftime("%H:%M")
    
    # Create order object
    order_data = {
        'order_id': order_id,
        'customer_name': customer_name,
        'phone': phone,
        'items': session['order'].copy(),
        'total': session['total'],
        'delivery_option': delivery_option,
        'location': location,
        'pickup_time': pickup_time,
        'order_time': order_time,
        'prep_time': prep_time,
        'ready_time': ready_time_str,
        'status': 'pending',
        'status_history': [
            {'status': 'pending', 'timestamp': order_time, 'note': 'Order received'}
        ]
    }
    
    # Save order to database
    orders = load_orders()
    orders[order_id] = order_data
    save_orders(orders)
    
    # Store order ID in session for confirmation
    session['current_order_id'] = order_id
    session['order_details'] = {
        'delivery_option': delivery_option,
        'location': location,
        'pickup_time': pickup_time,
        'prep_time': prep_time,
        'ready_time': ready_time_str,
        'phone': phone,
        'customer_name': customer_name
    }
    
    return redirect(url_for('confirmation'))

@app.route('/confirmation')
def confirmation():
    if 'current_order_id' not in session:
        return redirect(url_for('index'))
    
    order_id = session['current_order_id']
    orders = load_orders()
    order_data = orders.get(order_id, {})
    
    return render_template('confirmation.html',
                         order=session['order'],
                         total=session['total'],
                         menu=MENU,
                         emojis=ITEM_EMOJIS,
                         details=session['order_details'],
                         order_id=order_id,
                         order_data=order_data)

@app.route('/complete_order')
def complete_order():
    session.pop('order', None)
    session.pop('total', None)
    session.pop('order_details', None)
    session.pop('current_order_id', None)
    return redirect(url_for('index'))

# KITCHEN ADMIN ROUTES

@app.route('/kitchen')
def kitchen_dashboard():
    """Kitchen staff dashboard"""
    orders = load_orders()
    
    # Filter orders (exclude completed and cancelled for main view)
    active_orders = {k: v for k, v in orders.items() 
                    if v['status'] not in ['completed', 'cancelled']}
    completed_orders = {k: v for k, v in orders.items() 
                       if v['status'] in ['completed', 'cancelled']}
    
    return render_template('kitchen.html',
                         active_orders=active_orders,
                         completed_orders=completed_orders,
                         statuses=ORDER_STATUS,
                         menu=MENU,
                         emojis=ITEM_EMOJIS)

@app.route('/kitchen/order/<order_id>')
def kitchen_order_detail(order_id):
    """Detailed view of a specific order"""
    orders = load_orders()
    order = orders.get(order_id)
    
    if not order:
        return "Order not found", 404
    
    return render_template('kitchen_order_detail.html',
                         order=order,
                         statuses=ORDER_STATUS,
                         menu=MENU,
                         emojis=ITEM_EMOJIS)

@app.route('/api/update_order_status', methods=['POST'])
def update_order_status():
    """API endpoint to update order status"""
    order_id = request.json.get('order_id')
    new_status = request.json.get('status')
    note = request.json.get('note', '')
    
    orders = load_orders()
    
    if order_id in orders:
        orders[order_id]['status'] = new_status
        orders[order_id]['status_history'].append({
            'status': new_status,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'note': note
        })
        save_orders(orders)
        
        return jsonify({'success': True, 'message': 'Status updated'})
    
    return jsonify({'success': False, 'message': 'Order not found'}), 404

@app.route('/api/get_orders')
def get_orders():
    """API endpoint to get orders (for real-time updates)"""
    orders = load_orders()
    return jsonify(orders)

@app.route('/kitchen/analytics')
def kitchen_analytics():
    """Kitchen analytics dashboard"""
    orders = load_orders()
    
    # Basic analytics
    total_orders = len(orders)
    pending_orders = len([o for o in orders.values() if o['status'] == 'pending'])
    preparing_orders = len([o for o in orders.values() if o['status'] == 'preparing'])
    ready_orders = len([o for o in orders.values() if o['status'] == 'ready'])
    
    # Today's orders
    today = datetime.now().strftime("%Y-%m-%d")
    today_orders = [o for o in orders.values() if o['order_time'].startswith(today)]
    
    # Popular items
    item_counts = {}
    for order in orders.values():
        for item, quantity in order['items'].items():
            if item in item_counts:
                item_counts[item] += quantity
            else:
                item_counts[item] = quantity
    
    popular_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return render_template('kitchen_analytics.html',
                         total_orders=total_orders,
                         pending_orders=pending_orders,
                         preparing_orders=preparing_orders,
                         ready_orders=ready_orders,
                         today_orders=len(today_orders),
                         popular_items=popular_items,
                         emojis=ITEM_EMOJIS,
                         now=datetime.now())  # current time

if __name__ == '__main__':
    app.run(debug=True)