# run.py - Application entry point
import os
import atexit
import signal
import sys
from app import app, mongo
from copyparty_manager import start_copyparty, stop_copyparty, get_copyparty_status

def setup_mongodb():
    """Initialize MongoDB collections if needed"""
    with app.app_context():
        try:
            # Test MongoDB connection
            mongo.db.command('ping')
            print("MongoDB connection successful!")
            
            # Show database info
            db_stats = mongo.db.command('dbStats')
            print(f"Database: {db_stats['db']}")
            print(f"Collections: {db_stats['collections']}")
            
            # List existing collections
            collections = mongo.db.list_collection_names()
            if collections:
                print(f"Existing collections: {', '.join(collections)}")
            else:
                print("No collections found - ready for data migration")
                
        except Exception as e:
            print(f"MongoDB setup error: {e}")
            print("Make sure MongoDB is running and accessible.")


def create_admin_user():
    """Create a default admin user if none exists"""
    with app.app_context():
        from app.mongodb_models import User

        try:
            # Check if any admin exists
            admin = User.find_one({"role": "admin"})
            if not admin:
                # Create default admin
                admin = User.create_user(
                    username='admin',
                    email='admin@example.com',
                    password='admin123',  # Change this password!
                    first_name='Admin',
                    last_name='User',
                    role='admin'
                )
                print("Default admin user created!")
                print("Username: admin")
                print("Password: admin123")
                print("IMPORTANT: Change this password after first login!")
            else:
                print("Admin user already exists")
                
        except Exception as e:
            print(f"Could not create admin user: {e}")


def cleanup_on_exit():
    """Cleanup function called on application exit."""
    print("\n=== Shutting Down Services ===")
    stop_copyparty()

def signal_handler(signum, frame):
    """Handle interrupt signals."""
    print("\nReceived interrupt signal, shutting down...")
    cleanup_on_exit()
    sys.exit(0)

if __name__ == '__main__':
    # Register cleanup handlers
    atexit.register(cleanup_on_exit)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Get configuration
    env = os.getenv('FLASK_ENV', 'development')
    print(f"Starting application in {env} mode...")

    # Show current configuration
    print(f"Database: {app.config.get('MONGO_URI', 'Not configured')[:50]}...")
    print(f"Access Token Duration: {app.config['ACCESS_TOKEN_DURATION']}")
    print(f"Remember Me Duration: {app.config['REMEMBER_ACCESS_TOKEN_DURATION']}")

    # Start Copyparty server
    print("\n=== Starting Copyparty Server ===")
    copyparty_started = start_copyparty()
    if copyparty_started:
        status = get_copyparty_status()
        print(f"[OK] Copyparty running on {status['config']['host']}:{status['config']['port']}")
        print(f"[INFO] Files stored in: {status['config']['files_directory']}")
    else:
        print("[WARN] Warning: Copyparty failed to start. Document uploads may not work properly.")

    # Setup MongoDB connection and create admin user if in development
    print("\n=== Setting up Database ===")
    if env == 'development':
        setup_mongodb()
        create_admin_user()
    else:
        # In production, just test the connection
        setup_mongodb()

    # Get host and port from environment or use defaults
    host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))

    print(f"\n=== Starting Flask Server ===")
    print(f"Flask server starting on http://{host}:{port}")

    try:
        # Run the application
        app.run(
            host=host,
            port=port,
            debug=app.config['DEBUG'],
            use_reloader=app.config['DEBUG']
        )
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        cleanup_on_exit()