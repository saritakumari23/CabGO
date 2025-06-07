from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate # Import Migrate
from flask_cors import CORS
from config import config_by_name # Updated import
import os

db = SQLAlchemy()
migrate = Migrate() # Initialize Migrate instance

def create_app(config_name=None, config_class=None): # Modified signature
    if config_class:
        app_config = config_class
    elif config_name:
        app_config = config_by_name.get(config_name)
    else:
        # Default to 'dev' or use FLASK_CONFIG environment variable if set
        app_config = config_by_name.get(os.getenv('FLASK_CONFIG', 'dev'))

    app = Flask(__name__)
    app.config.from_object(app_config)

    CORS(app)  # Enable CORS for all routes
    db.init_app(app)
    migrate.init_app(app, db) # Initialize Migrate with app and db

    # Import models here so Flask-Migrate can detect them
    from .models import User, Location, Ride, DriverProfile, Vehicle

    # Register blueprints here
    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    from .rides import rides_bp
    app.register_blueprint(rides_bp, url_prefix='/api/rides')

    from .drivers import drivers_bp
    app.register_blueprint(drivers_bp, url_prefix='/api/drivers')

    from .vehicles import vehicles_bp
    app.register_blueprint(vehicles_bp, url_prefix='/api/vehicles')

    from .admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    # from .main import main_bp # Example for other general routes
    # app.register_blueprint(main_bp, url_prefix='/api')

    @app.route('/health')
    def health_check():
        return 'OK', 200

    return app
