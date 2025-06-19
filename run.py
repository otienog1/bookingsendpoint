# run.py - Application entry point
import os
from app import app, db
from flask_migrate import Migrate, init, migrate, upgrade

# Initialize Flask-Migrate
migrate_instance = Migrate(app, db)


def setup_database():
    """Initialize database if needed"""
    with app.app_context():
        try:
            # Try to create tables if they don't exist
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Database setup error: {e}")
            print("Tables might already exist or there's a connection issue.")


def create_admin_user():
    """Create a default admin user if none exists"""
    with app.app_context():
        from app.user import User

        # Check if any admin exists
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            try:
                # Create default admin
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    first_name='Admin',
                    last_name='User',
                    role='admin'
                )
                admin.set_password('admin123')  # Change this password!
                db.session.add(admin)
                db.session.commit()
                print("Default admin user created!")
                print("Username: admin")
                print("Password: admin123")
                print("IMPORTANT: Change this password after first login!")
            except Exception as e:
                print(f"Could not create admin user: {e}")


if __name__ == '__main__':
    # Get configuration
    env = os.getenv('FLASK_ENV', 'development')
    print(f"Starting application in {env} mode...")

    # Show current configuration
    print(f"Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"Access Token Duration: {app.config['ACCESS_TOKEN_DURATION']}")
    print(f"Remember Me Duration: {app.config['REMEMBER_ACCESS_TOKEN_DURATION']}")

    # Setup database if in development
    if env == 'development':
        setup_database()
        create_admin_user()

    # Get host and port from environment or use defaults
    host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))

    # Run the application
    app.run(
        host=host,
        port=port,
        debug=app.config['DEBUG'],
        use_reloader=app.config['DEBUG']
    )