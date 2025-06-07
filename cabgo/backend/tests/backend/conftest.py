import pytest
from app import create_app, db
from app.models import User # Import other models as needed for setup/teardown
from config import TestingConfig # Use TestingConfig

@pytest.fixture(scope='session')
def app():
    """Create and configure a new app instance for each test session."""
    # Pass TestingConfig directly to create_app
    app = create_app(config_class=TestingConfig)
    with app.app_context():
        db.create_all() # Create all tables
        yield app
        db.session.remove() # Clean up session
        db.drop_all()     # Drop all tables after tests are done

@pytest.fixture(scope='function') 
def client(app):
    """A test client for the app."""
    with app.test_client() as client:
        with app.app_context(): 
            yield client

@pytest.fixture(scope='function')
def init_database(app):
    """Fixture to ensure database is clean before each test function that needs it."""
    with app.app_context():
        # Clear data from all tables to ensure a clean slate for each test function
        meta = db.metadata
        for table in reversed(meta.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
    yield db

@pytest.fixture(scope='function')
def new_user_data():
    """Provides data for a new user registration."""
    return {
        'email': 'testuser@example.com',
        'password': 'password123',
        'full_name': 'Test User',
        'phone_number': '1234567890'
    }

@pytest.fixture(scope='function')
def admin_user_data():
    """Provides data for a new admin user registration."""
    return {
        'email': 'admin@example.com',
        'password': 'adminpassword',
        'full_name': 'Admin User',
        'phone_number': '0987654321',
        'is_admin': True # Key difference
    }

@pytest.fixture(scope='function')
def admin_auth_headers(client, admin_user_data, init_database):
    """Registers an admin user, logs them in, and returns auth headers.
    Depends on init_database to ensure a clean state.
    """
    # init_database fixture has already run and cleaned the DB.

    # 1. Register the user specified by admin_user_data
    # The /api/auth/register endpoint does not accept 'is_admin', so remove it.
    registration_payload = {k: v for k, v in admin_user_data.items() if k != 'is_admin'}
    reg_response = client.post('/api/auth/register', json=registration_payload)
    
    if reg_response.status_code != 201:
        raise Exception(f"Admin user registration failed in fixture: {reg_response.status_code} {reg_response.get_data(as_text=True)}")
    
    reg_json = reg_response.get_json()
    if 'user' not in reg_json or 'id' not in reg_json.get('user', {}):
        raise Exception(f"Admin user registration response in fixture missing 'user' or 'user.id': {reg_json}")
    # admin_user_id = reg_json['user']['id'] # Not strictly needed here, but good to know it exists

    # 2. Elevate this newly registered user to admin status
    with client.application.app_context():
        user_to_make_admin = User.query.filter_by(email=admin_user_data['email']).first()
        if not user_to_make_admin:
            # This should not happen if registration above was successful
            raise Exception(f"Failed to find user {admin_user_data['email']} immediately after registration in admin_auth_headers.")
        user_to_make_admin.is_admin = True
        db.session.add(user_to_make_admin) # Ensure change is staged
        db.session.commit()

    # 3. Log in as this new admin user
    login_payload = {'email': admin_user_data['email'], 'password': admin_user_data['password']}
    login_response = client.post('/api/auth/login', json=login_payload)

    if login_response.status_code != 200:
        raise Exception(f"Admin user login failed in fixture: {login_response.status_code} {login_response.get_data(as_text=True)}")
    
    login_json = login_response.get_json()
    token = login_json.get('token')
    if not token:
        raise Exception(f"Token not found in admin login response in fixture: {login_json}")

    return {'Authorization': f'Bearer {token}'}
