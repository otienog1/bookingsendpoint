from flask import Blueprint, jsonify, request, current_app
from .user import User
from . import db
import jwt
from datetime import datetime, timedelta
from functools import wraps

authbp = Blueprint("authbp", __name__)

# Token blacklist storage (in-memory for now, use Redis in production)
token_blacklist = set()


def is_token_blacklisted(token):
    """Check if token is blacklisted"""
    if current_app.config.get('ENABLE_TOKEN_BLACKLIST'):
        if hasattr(current_app, 'redis') and current_app.redis:
            try:
                return current_app.redis.sismember('blacklisted_tokens', token)
            except:
                pass
        return token in token_blacklist
    return False


def blacklist_token(token):
    """Add token to blacklist"""
    if current_app.config.get('ENABLE_TOKEN_BLACKLIST'):
        if hasattr(current_app, 'redis') and current_app.redis:
            try:
                # Decode token to get expiry
                decoded = jwt.decode(token, current_app.config['SECRET_KEY'],
                                     algorithms=[current_app.config['JWT_ALGORITHM']])
                ttl = decoded['exp'] - datetime.utcnow().timestamp()
                if ttl > 0:
                    current_app.redis.setex(f'blacklist:{token}', int(ttl), '1')
            except:
                pass
        else:
            token_blacklist.add(token)


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

        # Check if token is blacklisted
        if is_token_blacklisted(token):
            return jsonify({'error': 'Token has been revoked!'}), 401

        try:
            # Decode token
            data = jwt.decode(token, current_app.config['SECRET_KEY'],
                              algorithms=[current_app.config['JWT_ALGORITHM']])
            current_user = User.query.get(data['user_id'])

            if not current_user:
                return jsonify({'error': 'User no longer exists!'}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


# Refresh token decorator - only accepts refresh tokens
def refresh_token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Refresh token is missing!'}), 401

        # Check if token is blacklisted
        if is_token_blacklisted(token):
            return jsonify({'error': 'Refresh token has been revoked!'}), 401

        try:
            # Decode token
            data = jwt.decode(token, current_app.config['SECRET_KEY'],
                              algorithms=[current_app.config['JWT_ALGORITHM']])

            # Verify it's a refresh token
            if data.get('type') != 'refresh':
                return jsonify({'error': 'Invalid token type!'}), 401

            current_user = User.query.get(data['user_id'])

            if not current_user:
                return jsonify({'error': 'User no longer exists!'}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Refresh token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid refresh token!'}), 401

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

        current_app.logger.info(f"New user registered: {new_user.username}")
        return jsonify({'message': 'User registered successfully!', 'user': new_user.to_dict()}), 201

    except Exception as e:
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': str(e)}), 400


@authbp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing login credentials!'}), 400

    user = User.query.filter_by(username=data['username']).first()

    if not user or not user.check_password(data['password']):
        current_app.logger.warning(f"Failed login attempt for username: {data.get('username')}")
        return jsonify({'error': 'Invalid username or password!'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account is disabled!'}), 401

    # Check if user wants "remember me" functionality
    remember_me = data.get('remember_me', False)

    # Get token durations from configuration
    if remember_me:
        access_duration = current_app.config['REMEMBER_ACCESS_TOKEN_DURATION']
        refresh_duration = current_app.config['REMEMBER_REFRESH_TOKEN_DURATION']
        current_app.logger.info(f"User {user.username} logged in with Remember Me")
    else:
        access_duration = current_app.config['ACCESS_TOKEN_DURATION']
        refresh_duration = current_app.config['REFRESH_TOKEN_DURATION']
        current_app.logger.info(f"User {user.username} logged in")

    # Calculate expiration times
    token_expiration = datetime.utcnow() + access_duration
    refresh_expiration = datetime.utcnow() + refresh_duration

    # Generate JWT access token
    access_token = jwt.encode({
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'exp': token_expiration
    }, current_app.config['SECRET_KEY'], algorithm=current_app.config['JWT_ALGORITHM'])

    # Generate refresh token
    refresh_token = jwt.encode({
        'user_id': user.id,
        'type': 'refresh',
        'exp': refresh_expiration
    }, current_app.config['SECRET_KEY'], algorithm=current_app.config['JWT_ALGORITHM'])

    return jsonify({
        'message': 'Login successful!',
        'token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    })


@authbp.route('/auth/refresh', methods=['POST'])
@refresh_token_required
def refresh_token(current_user):
    """
    Refresh the JWT token using a refresh token
    """
    try:
        # Check if "remember me" was originally set (passed in request body)
        data = request.get_json() or {}
        remember_me = data.get('remember_me', False)

        # Get token duration from configuration
        if remember_me:
            access_duration = current_app.config['REMEMBER_ACCESS_TOKEN_DURATION']
        else:
            access_duration = current_app.config['ACCESS_TOKEN_DURATION']

        token_expiration = datetime.utcnow() + access_duration

        # Generate new JWT token with fresh expiration
        new_token = jwt.encode({
            'user_id': current_user.id,
            'username': current_user.username,
            'role': current_user.role,
            'exp': token_expiration
        }, current_app.config['SECRET_KEY'], algorithm=current_app.config['JWT_ALGORITHM'])

        current_app.logger.info(f"Token refreshed for user: {current_user.username}")

        return jsonify({
            'message': 'Token refreshed successfully',
            'token': new_token,
            'user': current_user.to_dict()
        })
    except Exception as e:
        current_app.logger.error(f"Token refresh error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@authbp.route('/auth/verify', methods=['GET'])
@token_required
def verify_token(current_user):
    """
    Verify if the current token is still valid
    Returns user info and remaining time
    """
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]

        try:
            decoded = jwt.decode(token, current_app.config['SECRET_KEY'],
                                 algorithms=[current_app.config['JWT_ALGORITHM']])
            exp_timestamp = decoded.get('exp', 0)
            current_timestamp = datetime.utcnow().timestamp()

            # Calculate remaining time in seconds
            remaining_seconds = max(0, exp_timestamp - current_timestamp)

            return jsonify({
                'valid': True,
                'user': current_user.to_dict(),
                'expires_in': remaining_seconds,
                'expires_at': exp_timestamp,
                'refresh_window': current_app.config['TOKEN_REFRESH_WINDOW']
            })
        except:
            pass

    return jsonify({'valid': False}), 401


@authbp.route('/auth/logout', methods=['POST'])
@token_required
def logout(current_user):
    """
    Logout endpoint - blacklists the current tokens
    """
    try:
        # Get both tokens from request
        auth_header = request.headers.get('Authorization')
        refresh_token = request.json.get('refresh_token') if request.json else None

        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ')[1]
            blacklist_token(access_token)

        if refresh_token:
            blacklist_token(refresh_token)

        current_app.logger.info(f"User {current_user.username} logged out")
        return jsonify({'message': 'Logged out successfully'})
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500


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
        current_app.logger.info(f"User {user.username} updated by {current_user.username}")
        return jsonify({'message': 'User updated successfully!', 'user': user.to_dict()})

    except Exception as e:
        current_app.logger.error(f"User update error: {str(e)}")
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
        current_app.logger.info(f"User {user.username} deleted by {current_user.username}")
        return jsonify({'message': 'User deleted successfully!'})
    except Exception as e:
        current_app.logger.error(f"User deletion error: {str(e)}")
        return jsonify({'error': str(e)}), 400


@authbp.route('/auth/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify({'user': current_user.to_dict()})


# Health check endpoint for authentication service
@authbp.route('/auth/health', methods=['GET'])
def health_check():
    """Check if authentication service is running"""
    return jsonify({
        'status': 'healthy',
        'service': 'authentication',
        'timestamp': datetime.utcnow().isoformat(),
        'features': {
            'token_refresh': True,
            'remember_me': True,
            'blacklist_enabled': current_app.config.get('ENABLE_TOKEN_BLACKLIST', False)
        }
    })