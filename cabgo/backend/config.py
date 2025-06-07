import os
import datetime # Added missing import
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env')) # Load environment variables from .env

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-default-secret-key-for-dev'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=1) # Example: 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=30) # Example: 30 days
    # Add other general configurations here

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    # Add development-specific configurations here

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'test.db') # Use a separate DB for testing
    WTF_CSRF_ENABLED = False # Disable CSRF forms in testing for convenience
    DEBUG = True # Often helpful for debugging tests
    # Ensure JWT tokens expire quickly or use fixed tokens for testing if needed
    # For simplicity, we'll use the default expiry for now.

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db') # Default to app.db if not set
    # Add production-specific configurations here
    # For example, ensure DEBUG and TESTING are False
    DEBUG = False
    TESTING = False

# Dictionary to access config classes by name
config_by_name = dict(
    dev=DevelopmentConfig,
    test=TestingConfig,
    prod=ProductionConfig,
    default=DevelopmentConfig
)
