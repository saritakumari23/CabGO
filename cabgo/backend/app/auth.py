from flask import Blueprint, request, jsonify
from .models import User
from . import db # Import db from the current app package's __init__.py
import datetime
from datetime import timezone # Import timezone
import jwt # PyJWT
from flask import current_app # To access app.config
from .decorators import token_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    phone_number = data.get('phone_number')
    # is_driver = data.get('is_driver', False) # Optional, defaults to False (passenger)

    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'User with this email already exists'}), 409 # Conflict
    
    if phone_number and User.query.filter_by(phone_number=phone_number).first():
        return jsonify({'message': 'User with this phone number already exists'}), 409

    new_user = User(
        email=email,
        full_name=full_name,
        phone_number=phone_number
        # is_driver=is_driver # Uncomment if you want to set this at registration
    )
    new_user.set_password(password)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'message': 'User registered successfully', 'user': {'id': new_user.id, 'email': new_user.email, 'full_name': new_user.full_name, 'phone_number': new_user.phone_number}}), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during registration: {e}")
        return jsonify({'message': 'Registration failed due to an internal error'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({'message': 'Invalid email or password'}), 401 # Unauthorized

    # Generate JWT token
    token_payload = {
        'user_id': user.id,
        'exp': datetime.datetime.now(timezone.utc) + datetime.timedelta(hours=current_app.config.get('JWT_EXPIRATION_HOURS', 24))
    }
    token = jwt.encode(
        token_payload,
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )

    return jsonify({'message': 'Login successful', 'token': token}), 200

# Logout route can be added later (often handled client-side by discarding the token)

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    if not current_user:
        return jsonify({'message': 'Authentication required'}), 401
    
    user_data = {
        'id': current_user.id,
        'email': current_user.email,
        'full_name': current_user.full_name,
        'phone_number': current_user.phone_number,
        'is_driver': current_user.is_driver,
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None,
        'updated_at': current_user.updated_at.isoformat() if current_user.updated_at else None
    }
    return jsonify(user_data), 200

