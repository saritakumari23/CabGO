import json
from app.models import User

def test_register_user(client, new_user_data, init_database):
    """Test user registration."""
    response = client.post('/api/auth/register', json=new_user_data)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}. Response: {response.data.decode()}"
    json_data = response.get_json()
    assert json_data['message'] == 'User registered successfully'
    
    user = User.query.filter_by(email=new_user_data['email']).first()
    assert user is not None
    assert user.full_name == new_user_data['full_name']

def test_register_user_duplicate_email(client, new_user_data, init_database):
    """Test registration with a duplicate email."""
    client.post('/api/auth/register', json=new_user_data) # First registration
    response = client.post('/api/auth/register', json=new_user_data) # Attempt duplicate
    assert response.status_code == 409, f"Expected 409, got {response.status_code}. Response: {response.data.decode()}"
    json_data = response.get_json()
    assert 'User with this email already exists' in json_data['message']

def test_login_user(client, new_user_data, init_database):
    """Test user login with correct credentials."""
    client.post('/api/auth/register', json=new_user_data)
    login_data = {'email': new_user_data['email'], 'password': new_user_data['password']}
    response = client.post('/api/auth/login', json=login_data)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.data.decode()}"
    json_data = response.get_json()
    assert 'token' in json_data
    assert json_data['message'] == 'Login successful'
    # User details are not part of the login response in the current implementation

def test_login_user_invalid_email(client, new_user_data, init_database):
    """Test user login with an invalid email."""
    login_data = {'email': 'wrongemail@example.com', 'password': new_user_data['password']}
    response = client.post('/api/auth/login', json=login_data)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}. Response: {response.data.decode()}"
    json_data = response.get_json()
    assert 'Invalid email or password' in json_data['message']

def test_login_user_wrong_password(client, new_user_data, init_database):
    """Test user login with a wrong password."""
    client.post('/api/auth/register', json=new_user_data)
    login_data = {'email': new_user_data['email'], 'password': 'wrongpassword'}
    response = client.post('/api/auth/login', json=login_data)
    assert response.status_code == 401, f"Expected 401, got {response.status_code}. Response: {response.data.decode()}"
    json_data = response.get_json()
    assert 'Invalid email or password' in json_data['message']
