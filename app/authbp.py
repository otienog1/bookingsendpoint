from flask import Blueprint, jsonify, request, current_app
from .mongodb_models import User
from . import mongo
from bson import ObjectId
import jwt
from datetime import datetime, timedelta
from functools import wraps
import secrets
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_SUPPORT = True
except ImportError:
    EMAIL_SUPPORT = False

authbp = Blueprint("authbp", __name__)

# Token blacklist storage (in-memory for now, use Redis in production)
token_blacklist = set()

# Password reset token storage (in-memory for now, use Redis in production)
password_reset_tokens = {}


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


def send_password_reset_email(email, reset_token):
    """Send password reset email"""
    if not EMAIL_SUPPORT:
        current_app.logger.warning("Email support not available - password reset email not sent")
        # In development, just log the reset token
        current_app.logger.info(f"Password reset token for {email}: {reset_token}")
        return True
        
    try:
        # Email configuration from app config
        smtp_server = current_app.config.get('SMTP_SERVER', 'localhost')
        smtp_port = current_app.config.get('SMTP_PORT', 587)
        smtp_username = current_app.config.get('SMTP_USERNAME')
        smtp_password = current_app.config.get('SMTP_PASSWORD')
        from_email = current_app.config.get('FROM_EMAIL', 'noreply@safaribuookings.com')
        
        # Create the email message
        msg = MimeMultipart('alternative')
        msg['Subject'] = 'Password Reset Request - Safari Bookings'
        msg['From'] = from_email
        msg['To'] = email
        
        # Create the reset URL
        frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
        reset_url = f"{frontend_url}/reset-password?token={reset_token}"
        
        # Email content
        text_content = f"""
        Hello,
        
        You have requested to reset your password for your Safari Bookings account.
        
        Please click on the following link to reset your password:
        {reset_url}
        
        This link will expire in 1 hour for security reasons.
        
        If you did not request this password reset, please ignore this email.
        
        Best regards,
        Safari Bookings Team
        """
        
        html_content = f"""
        <html>
        <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #2563eb;">Password Reset Request</h2>
                <p>Hello,</p>
                <p>You have requested to reset your password for your Safari Bookings account.</p>
                <p>Please click on the button below to reset your password:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" 
                       style="background-color: #2563eb; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 6px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                <p style="font-size: 14px; color: #666;">
                    If the button doesn't work, you can also copy and paste this link into your browser:
                </p>
                <p style="font-size: 14px; color: #666; word-break: break-all;">
                    {reset_url}
                </p>
                <p style="font-size: 14px; color: #666;">
                    This link will expire in 1 hour for security reasons.
                </p>
                <p style="font-size: 14px; color: #666;">
                    If you did not request this password reset, please ignore this email.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #999;">
                    Best regards,<br>
                    Safari Bookings Team
                </p>
            </div>
        </body>
        </html>
        """
        
        # Attach parts
        part1 = MimeText(text_content, 'plain')
        part2 = MimeText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send the email
        if smtp_username and smtp_password:
            # Use SMTP with authentication
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            server.quit()
        else:
            # Use local SMTP without authentication (for development)
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.send_message(msg)
            server.quit()
            
        current_app.logger.info(f"Password reset email sent to {email}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email to {email}: {str(e)}")
        return False


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
            current_user = User.find_by_id(data['user_id'])

            if not current_user:
                return jsonify({'error': 'User no longer exists!'}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 401
        except Exception as e:
            current_app.logger.error(f"Token validation error: {str(e)}")
            return jsonify({'error': 'Token validation failed!'}), 401

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

            current_user = User.find_by_id(data['user_id'])

            if not current_user:
                return jsonify({'error': 'User no longer exists!'}), 401

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Refresh token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid refresh token!'}), 401
        except Exception as e:
            current_app.logger.error(f"Refresh token validation error: {str(e)}")
            return jsonify({'error': 'Refresh token validation failed!'}), 401

        return f(current_user, *args, **kwargs)

    return decorated


@authbp.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()

    try:
        # Check if user already exists
        existing_user = User.find_by_username(data['username'])
        if existing_user:
            return jsonify({'error': 'Username already exists!'}), 400

        existing_email = User.find_by_email(data['email'])
        if existing_email:
            return jsonify({'error': 'Email already registered!'}), 400

        # Create new user
        new_user = User.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            role=data.get('role', 'user')
        )

        current_app.logger.info(f"New user registered: {new_user['username']}")
        return jsonify({'message': 'User registered successfully!', 'user': User.to_dict(new_user)}), 201

    except Exception as e:
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': str(e)}), 400


@authbp.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing login credentials!'}), 400

    user = User.find_by_username(data['username'])

    if not user or not User.check_password(user, data['password']):
        current_app.logger.warning(f"Failed login attempt for username: {data.get('username')}")
        return jsonify({'error': 'Invalid username or password!'}), 401

    if not user['is_active']:
        return jsonify({'error': 'Account is disabled!'}), 401

    # Check if user wants "remember me" functionality
    remember_me = data.get('remember_me', False)

    # Get token durations from configuration
    if remember_me:
        access_duration = current_app.config['REMEMBER_ACCESS_TOKEN_DURATION']
        refresh_duration = current_app.config['REMEMBER_REFRESH_TOKEN_DURATION']
        current_app.logger.info(f"User {user['username']} logged in with Remember Me")
    else:
        access_duration = current_app.config['ACCESS_TOKEN_DURATION']
        refresh_duration = current_app.config['REFRESH_TOKEN_DURATION']
        current_app.logger.info(f"User {user['username']} logged in")

    # Calculate expiration times
    token_expiration = datetime.utcnow() + access_duration
    refresh_expiration = datetime.utcnow() + refresh_duration

    # Generate JWT access token
    access_token = jwt.encode({
        'user_id': str(user['_id']),
        'username': user['username'],
        'role': user['role'],
        'exp': token_expiration
    }, current_app.config['SECRET_KEY'], algorithm=current_app.config['JWT_ALGORITHM'])

    # Generate refresh token
    refresh_token = jwt.encode({
        'user_id': str(user['_id']),
        'type': 'refresh',
        'exp': refresh_expiration
    }, current_app.config['SECRET_KEY'], algorithm=current_app.config['JWT_ALGORITHM'])

    return jsonify({
        'message': 'Login successful!',
        'token': access_token,
        'refresh_token': refresh_token,
        'user': User.to_dict(user)
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
            'user_id': str(current_user['_id']),
            'username': current_user['username'],
            'role': current_user['role'],
            'exp': token_expiration
        }, current_app.config['SECRET_KEY'], algorithm=current_app.config['JWT_ALGORITHM'])

        current_app.logger.info(f"Token refreshed for user: {current_user['username']}")

        return jsonify({
            'message': 'Token refreshed successfully',
            'token': new_token,
            'user': User.to_dict(current_user)
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
                'user': User.to_dict(current_user),
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

        current_app.logger.info(f"User {current_user['username']} logged out")
        return jsonify({'message': 'Logged out successfully'})
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500


@authbp.route('/auth/users', methods=['GET'])
@token_required
def get_users(current_user):
    if current_user['role'] != 'admin':
        return jsonify({'error': 'Unauthorized access!'}), 403

    users = User.get_all()
    return jsonify({'users': [User.to_dict(user) for user in users]})


def _get_user_logic(current_user, user_id):
    """Shared logic for getting user by ID."""
    # Users can view their own profile, admins can view any profile
    if str(current_user['_id']) != user_id and current_user['role'] != 'admin':
        return jsonify({'error': 'Unauthorized access!'}), 403

    user = User.find_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found!'}), 404

    return jsonify({'user': User.to_dict(user)})


@authbp.route('/auth/user/<user_id>', methods=['GET'])
@token_required
def get_user(current_user, user_id):
    """Original user fetch endpoint."""
    return _get_user_logic(current_user, user_id)


@authbp.route('/api/auth/user/<user_id>', methods=['GET'])
@token_required
def api_get_user(current_user, user_id):
    """API endpoint alias for getting user by ID."""
    return _get_user_logic(current_user, user_id)


@authbp.route('/auth/user/<user_id>', methods=['PUT'])
@token_required
def update_user(current_user, user_id):
    # Users can update their own profile, admins can update any profile
    if str(current_user['_id']) != user_id and current_user['role'] != 'admin':
        return jsonify({'error': 'Unauthorized access!'}), 403

    user = User.find_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found!'}), 404

    data = request.get_json()

    try:
        update_data = {}
        
        # Update user fields
        if 'email' in data:
            existing_email = User.find_by_email(data['email'])
            if existing_email and str(existing_email['_id']) != user_id:
                return jsonify({'error': 'Email already registered!'}), 400
            update_data['email'] = data['email']

        if 'first_name' in data:
            update_data['first_name'] = data['first_name']

        if 'last_name' in data:
            update_data['last_name'] = data['last_name']

        # Only admins can change roles
        if 'role' in data and current_user['role'] == 'admin':
            update_data['role'] = data['role']

        if 'is_active' in data and current_user['role'] == 'admin':
            update_data['is_active'] = data['is_active']

        # Update password if provided
        if 'password' in data:
            User.update_password(user_id, data['password'])

        # Update other fields
        if update_data:
            User.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )

        # Get updated user
        updated_user = User.find_by_id(user_id)
        current_app.logger.info(f"User {updated_user['username']} updated by {current_user['username']}")
        return jsonify({'message': 'User updated successfully!', 'user': User.to_dict(updated_user)})

    except Exception as e:
        current_app.logger.error(f"User update error: {str(e)}")
        return jsonify({'error': str(e)}), 400


@authbp.route('/auth/user/<user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    # Only admins can delete users
    if current_user['role'] != 'admin':
        return jsonify({'error': 'Unauthorized access!'}), 403

    user = User.find_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found!'}), 404

    # Prevent deleting the last admin account
    if user['role'] == 'admin':
        admin_count = len(User.find_many({"role": "admin"}))
        if admin_count <= 1:
            return jsonify({'error': 'Cannot delete the last admin account!'}), 400

    try:
        User.delete_one({"_id": ObjectId(user_id)})
        current_app.logger.info(f"User {user['username']} deleted by {current_user['username']}")
        return jsonify({'message': 'User deleted successfully!'})
    except Exception as e:
        current_app.logger.error(f"User deletion error: {str(e)}")
        return jsonify({'error': str(e)}), 400


@authbp.route('/auth/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    return jsonify({'user': User.to_dict(current_user)})


@authbp.route('/auth/forgot-password', methods=['POST'])
def forgot_password():
    """
    Initiate password reset process
    """
    data = request.get_json()
    
    if not data or not data.get('email'):
        return jsonify({'error': 'Email is required!'}), 400
    
    email = data['email'].lower().strip()
    
    try:
        # Find user by email
        user = User.find_by_email(email)
        
        # Always return success message for security (don't reveal if email exists)
        if user:
            if not user['is_active']:
                current_app.logger.warning(f"Password reset attempt for inactive user: {email}")
            else:
                # Generate secure reset token
                reset_token = secrets.token_urlsafe(32)
                
                # Store token with expiration (1 hour)
                expiration = datetime.utcnow() + timedelta(hours=1)
                password_reset_tokens[reset_token] = {
                    'user_id': str(user['_id']),
                    'email': email,
                    'expires_at': expiration
                }
                
                # Send password reset email
                if send_password_reset_email(email, reset_token):
                    current_app.logger.info(f"Password reset initiated for user: {email}")
                else:
                    current_app.logger.error(f"Failed to send reset email for user: {email}")
                    return jsonify({'error': 'Failed to send reset email. Please try again.'}), 500
        else:
            current_app.logger.warning(f"Password reset attempt for non-existent email: {email}")
        
        return jsonify({
            'message': 'If an account with that email exists, we have sent a password reset link.'
        })
        
    except Exception as e:
        current_app.logger.error(f"Forgot password error: {str(e)}")
        return jsonify({'error': 'An error occurred. Please try again.'}), 500


@authbp.route('/auth/reset-password', methods=['POST'])
def reset_password():
    """
    Reset password using reset token
    """
    data = request.get_json()
    
    if not data or not data.get('token') or not data.get('password'):
        return jsonify({'error': 'Token and new password are required!'}), 400
    
    reset_token = data['token']
    new_password = data['password']
    
    try:
        # Check if token exists and is valid
        if reset_token not in password_reset_tokens:
            return jsonify({'error': 'Invalid or expired reset token!'}), 400
        
        token_data = password_reset_tokens[reset_token]
        
        # Check if token has expired
        if datetime.utcnow() > token_data['expires_at']:
            # Clean up expired token
            del password_reset_tokens[reset_token]
            return jsonify({'error': 'Reset token has expired!'}), 400
        
        # Validate password strength
        if len(new_password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters long!'}), 400
        
        # Find user
        user = User.find_by_id(token_data['user_id'])
        if not user:
            # Clean up token
            del password_reset_tokens[reset_token]
            return jsonify({'error': 'User no longer exists!'}), 404
        
        if not user['is_active']:
            # Clean up token
            del password_reset_tokens[reset_token]
            return jsonify({'error': 'Account is disabled!'}), 401
        
        # Update password
        User.update_password(token_data['user_id'], new_password)
        
        # Clean up the used token
        del password_reset_tokens[reset_token]
        
        current_app.logger.info(f"Password successfully reset for user: {user['username']}")
        
        return jsonify({
            'message': 'Password has been reset successfully! You can now sign in with your new password.'
        })
        
    except Exception as e:
        current_app.logger.error(f"Reset password error: {str(e)}")
        return jsonify({'error': 'An error occurred while resetting password. Please try again.'}), 500


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