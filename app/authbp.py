from flask import Blueprint, jsonify, request, current_app
from .user import User
from . import db
import jwt
from datetime import datetime, timedelta
from functools import wraps

authbp = Blueprint("authbp", __name__)

# Authentication decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401
        
        try:
            # Decode token
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            
            if not current_user:
                return jsonify({'error': 'User no longer exists!'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated


@authbp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    
    try:
        # Check if user already exists
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({'error': 'Username already exists!'}), 400
            
        existing_email = User.query.filter_by(email=data['email']).first()
        if existing_email:
            return jsonify({'error': 'Email already registered!'}), 400
        
        # Create new user
        new_user = User(
            username=data['username'],
            email=data['email'],
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            role=data.get('role', 'user')
        )
        new_user.set_password(data['password'])
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({'message': 'User registered successfully!', 'user': new_user.to_dict()}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@authbp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing login credentials!'}), 400
        
    user = User.query.filter_by(username=data['username']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password!'}), 401
        
    if not user.is_active:
        return jsonify({'error': 'Account is disabled!'}), 401
    
    # Generate JWT token
    token = jwt.encode({
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm="HS256")
    
    return jsonify({
        'message': 'Login successful!',
        'token': token,
        'user': user.to_dict()
    })


@authbp.route('/auth/users', methods=['GET'])
@token_required
def get_users(current_user):
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access!'}), 403
        
    users = User.query.all()
    return jsonify({'users': [user.to_dict() for user in users]})


@authbp.route('/auth/user/<int:user_id>', methods=['GET'])
@token_required
def get_user(current_user, user_id):
    # Users can view their own profile, admins can view any profile
    if current_user.id != user_id and current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access!'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found!'}), 404
        
    return jsonify({'user': user.to_dict()})


@authbp.route('/auth/user/<int:user_id>', methods=['PUT'])
@token_required
def update_user(current_user, user_id):
    # Users can update their own profile, admins can update any profile
    if current_user.id != user_id and current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access!'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found!'}), 404
    
    data = request.get_json()
    
    try:
        # Update user fields
        if 'email' in data:
            existing_email = User.query.filter_by(email=data['email']).first()
            if existing_email and existing_email.id != user_id:
                return jsonify({'error': 'Email already registered!'}), 400
            user.email = data['email']
            
        if 'first_name' in data:
            user.first_name = data['first_name']
            
        if 'last_name' in data:
            user.last_name = data['last_name']
        
        # Only admins can change roles
        if 'role' in data and current_user.role == 'admin':
            user.role = data['role']
            
        if 'is_active' in data and current_user.role == 'admin':
            user.is_active = data['is_active']
            
        # Update password if provided
        if 'password' in data:
            user.set_password(data['password'])
            
        db.session.commit()
        return jsonify({'message': 'User updated successfully!', 'user': user.to_dict()})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@authbp.route('/auth/user/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    # Only admins can delete users
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access!'}), 403
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found!'}), 404
        
    # Prevent deleting the last admin account
    if user.role == 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            return jsonify({'error': 'Cannot delete the last admin account!'}), 400
    
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@authbp.route('/auth/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify({'user': current_user.to_dict()})