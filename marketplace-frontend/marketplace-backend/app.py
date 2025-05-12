# === Imports ===
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
import os
import random

from models import db, User, Listing, Transaction, Review, CartItem

# === App Configuration ===
app = Flask(__name__)
CORS(app, origins=['http://localhost:3000'])

UPLOAD_FOLDER = os.path.join(app.root_path, 'static/uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# === Serve Uploaded Files ===
@app.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# === Authentication Routes ===
@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists'}), 409
    hashed_password = generate_password_hash(data['password'])
    user = User(username=data['username'], password=hashed_password, balance=100.0)
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User created!'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Login successful', 'user_id': user.id})
    return jsonify({'message': 'Invalid credentials'}), 401

# === Listings Routes ===
@app.route('/listings', methods=['POST'])
def create_listing():
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        price = float(request.form.get('price'))
        user_id = int(request.form.get('user_id'))
        quantity = int(request.form.get('quantity', 1))

        image = request.files.get('image')
        image_url = ''
        if image:
            filename = secure_filename(image.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)
            image_url = f'/static/uploads/{filename}'
        listing = Listing(title=title, description=description, price=price, user_id=user_id, image_url=image_url, quantity=quantity)
        db.session.add(listing)
        db.session.commit()
        return jsonify({'message': 'Listing created!'}), 201
    except Exception:
        return jsonify({'error': 'Server error creating listing'}), 500

@app.route('/listings', methods=['GET'])
def get_listings():
    listings = Listing.query.filter_by(is_sold=False).all()
    return jsonify([{
        'id': l.id,
        'title': l.title,
        'description': l.description,
        'price': l.price,
        'user_id': l.user_id,
        'image_url': l.image_url,
        'quantity': l.quantity
    } for l in listings])

@app.route('/listings/<int:id>', methods=['DELETE'])
def delete_listing(id):
    data = request.get_json()
    user_id = data.get('user_id')
    listing = Listing.query.get(id)
    if listing and listing.user_id == user_id:
        db.session.delete(listing)
        db.session.commit()
        return jsonify({'message': 'Listing deleted'})
    return jsonify({'message': 'Unauthorized or listing not found'}), 403

@app.route('/listings/<int:id>', methods=['PUT'])
def update_listing(id):
    listing = Listing.query.get(id)
    if not listing:
        return jsonify({'error': 'Listing not found'}), 404
    user_id = int(request.form.get('user_id'))
    if listing.user_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    listing.title = request.form.get('title', listing.title)
    listing.description = request.form.get('description', listing.description)
    listing.price = float(request.form.get('price', listing.price))
    image = request.files.get('image')
    if image:
        filename = secure_filename(image.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)
        listing.image_url = f'/static/uploads/{filename}'
    db.session.commit()
    return jsonify({'message': 'Listing updated'})

# === Transaction Routes (Buy, Cancel Orders) ===
@app.route('/buy/<int:listing_id>', methods=['POST'])
def buy_listing(listing_id):
    data = request.get_json()
    buyer_id = int(data.get('user_id'))
    quantity = int(data.get('quantity', 1))  # default to 1 if missing
    shipping_address = data.get('shipping_address', '')

    listing = Listing.query.get(listing_id)
    buyer = User.query.get(buyer_id)
    seller = User.query.get(listing.user_id) if listing else None

    if not listing or listing.quantity < quantity:
        return jsonify({'error': 'Not enough quantity available'}), 400
    if not buyer or not seller:
        return jsonify({'error': 'Invalid buyer or seller'}), 400

    total_price = listing.price * quantity
    if buyer.balance < total_price:
        return jsonify({'error': 'Insufficient balance'}), 400

    # Update balances and listing inventory
    buyer.balance -= total_price
    seller.balance += total_price
    listing.quantity -= quantity
    if listing.quantity == 0:
        listing.is_sold = True

    estimate = (datetime.utcnow() + timedelta(days=2 + listing.id % 4)).strftime("%Y-%m-%d")
    purchase_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    transaction = Transaction(
        buyer_id=buyer.id,
        seller_id=seller.id,
        listing_id=listing.id,
        price=listing.price,
        quantity=quantity,
        shipping_address=shipping_address,
        delivery_estimate=estimate,
        purchase_datetime=purchase_time,
        status="In Progress"
    )

    CartItem.query.filter_by(user_id=buyer_id, listing_id=listing_id).delete()

    db.session.add(transaction)
    db.session.commit()
    return jsonify({'message': 'Purchase complete', 'estimate': estimate})

@app.route('/cancel/<int:transaction_id>', methods=['POST'])
def cancel_order(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if not transaction:
        return jsonify({'error': 'Transaction not found'}), 404

    if transaction.status != 'In Progress':
        return jsonify({'error': 'Transaction cannot be cancelled'}), 403

    now = datetime.utcnow()
    purchase_time = datetime.strptime(transaction.purchase_datetime, "%Y-%m-%d %H:%M:%S")
    if (now - purchase_time) > timedelta(hours=24):
        return jsonify({'error': 'Cancellation window expired'}), 403

    buyer = User.query.get(transaction.buyer_id)
    seller = User.query.get(transaction.seller_id)
    listing = Listing.query.get(transaction.listing_id)

    if not all([buyer, seller, listing]):
        return jsonify({'error': 'Missing data to process refund'})

    # Refund and restore inventory
    buyer.balance += transaction.price * transaction.quantity
    seller.balance -= transaction.price * transaction.quantity
    listing.quantity += transaction.quantity
    transaction.status = "Cancelled"

    db.session.commit()
    return jsonify({'message': 'Order cancelled and refunded'})

# === Profile Route ===
@app.route('/profile/<int:user_id>', methods=['GET'])
def get_profile(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    purchases = Transaction.query.filter_by(buyer_id=user_id).all()
    sales = Transaction.query.filter_by(seller_id=user_id).all()
    return jsonify({
        'username': user.username,
        'balance': user.balance,
        'purchases': [{
            'listing_id': t.listing_id,
            'price': t.price,
            'quantity': t.quantity,
            'date': t.delivery_estimate,
            'shipping_address': t.shipping_address,
            'purchase_datetime': t.purchase_datetime,
            'status': t.status,
            'transaction_id': t.id
        } for t in purchases],
        'sales': [{
            'listing_id': t.listing_id,
            'price': t.price,
            'date': t.delivery_estimate,
            'buyer_id': t.buyer_id,
            'purchase_datetime': t.purchase_datetime,
            'status': t.status
        } for t in sales]
    })

# === Reviews Routes ===
@app.route('/reviews/<int:listing_id>', methods=['GET'])
def get_reviews(listing_id):
    reviews = Review.query.filter_by(listing_id=listing_id).all()
    return jsonify([{
        'id': r.id,
        'user_id': r.user_id,
        'rating': r.rating,
        'comment': r.comment,
        'timestamp': r.timestamp
    } for r in reviews])

@app.route('/reviews/<int:listing_id>', methods=['POST'])
def post_review(listing_id):
    data = request.get_json()
    user_id = data.get('user_id')
    rating = int(data.get('rating'))
    comment = data.get('comment', '')
    if not (1 <= rating <= 5):
        return jsonify({'error': 'Rating must be 1–5'}), 400
    new_review = Review(
        user_id=user_id,
        listing_id=listing_id,
        rating=rating,
        comment=comment,
        timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.session.add(new_review)
    db.session.commit()
    return jsonify({'message': 'Review submitted'})

# === Cart Routes ===
@app.route('/cart/<int:user_id>', methods=['GET'])
def get_cart(user_id):
    items = CartItem.query.filter_by(user_id=user_id).all()
    listings = []
    for item in items:
        listing = Listing.query.get(item.listing_id)
        if listing:
            listings.append({
                'id': listing.id,
                'title': listing.title,
                'description': listing.description,
                'price': listing.price,
                'image_url': listing.image_url,
                'quantity': listing.quantity
            })
    return jsonify(listings)

@app.route('/cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    user_id = data['user_id']
    listing_id = data['listing_id']
    quantity = int(data.get('quantity', 1))

    existing = CartItem.query.filter_by(user_id=user_id, listing_id=listing_id).first()
    if existing:
        return jsonify({'message': 'Item already in cart'}), 400

    listing = Listing.query.get(listing_id)
    if not listing or quantity > listing.quantity:
        return jsonify({'error': 'Invalid quantity'}), 400

    new_item = CartItem(user_id=user_id, listing_id=listing_id, quantity=quantity)
    db.session.add(new_item)
    db.session.commit()
    return jsonify({'message': 'Item added to cart'})

@app.route('/cart', methods=['DELETE'])
def remove_from_cart():
    data = request.get_json()
    user_id = data.get('user_id')
    listing_id = data.get('listing_id')

    item = CartItem.query.filter_by(user_id=user_id, listing_id=listing_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        return jsonify({'message': 'Removed from cart'})
    return jsonify({'error': 'Item not found'}), 404

# === Wallet / Deposit Route ===
@app.route('/wallet/deposit', methods=['POST'])
def deposit():
    data = request.get_json()
    user_id = data.get('user_id')
    amount = float(data.get('amount', 0))

    if not user_id or amount <= 0:
        return jsonify({'error': 'Invalid deposit data'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.balance += amount
    db.session.commit()
    return jsonify({'message': 'Deposit successful', 'new_balance': user.balance})

# === Random ===
@app.route('/random', methods=['GET'])
def get_random_listings():
    listings = Listing.query.filter_by(is_sold=False).all()
    sample = random.sample(listings, min(5, len(listings)))
    return jsonify([{
        'id': l.id,
        'title': l.title,
        'description': l.description,
        'price': l.price,
        'user_id': l.user_id,
        'image_url': l.image_url
    } for l in sample])

# === Run App ===
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
