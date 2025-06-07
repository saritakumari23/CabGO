import pytest
import json
from app import db
from app.models import User, DriverProfile

@pytest.fixture(scope='function')
def driver_user_data():
    """Provides data for a new user who will become a driver."""
    return {
        'email': 'driver@example.com',
        'password': 'driverpassword',
        'full_name': 'Driver User',
        'phone_number': '1122334455',
        'is_admin': False
    }

@pytest.fixture(scope='function')
def driver_auth_headers(client, driver_user_data, init_database):
    """Registers a user, makes them a driver, logs them in, and returns auth headers."""
    # Register the user
    registration_payload = {k: v for k, v in driver_user_data.items() if k != 'is_admin'}
    reg_response = client.post('/api/auth/register', json=registration_payload)
    assert reg_response.status_code == 201
    user_id = reg_response.get_json()['user']['id']

    # Create a DriverProfile for this user
    with client.application.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        user.is_driver = True # Mark as driver
        driver_profile = DriverProfile(
            user_id=user.id,
            license_number=f'DRIVERLIC{user.id}', # Unique license
            availability_status='OFFLINE' # Initial status
        )
        db.session.add(user)
        db.session.add(driver_profile)
        db.session.commit()

    # Log in as this new driver user
    login_payload = {'email': driver_user_data['email'], 'password': driver_user_data['password']}
    login_response = client.post('/api/auth/login', json=login_payload)
    assert login_response.status_code == 200
    token = login_response.get_json().get('token')
    assert token is not None

    return {'Authorization': f'Bearer {token}'}

def test_update_availability_success(client, driver_auth_headers, init_database):
    """Test successful update of driver availability status."""
    headers = driver_auth_headers
    payload = {'availability_status': 'AVAILABLE'}

    response = client.patch('/api/drivers/availability', headers=headers, json=payload)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['message'] == 'Driver availability updated successfully.'
    assert json_data['new_status'] == 'AVAILABLE'

    # Verify in DB
    with client.application.app_context():
        driver_user = User.query.filter_by(email='driver@example.com').first()
        assert driver_user is not None
        driver_profile = DriverProfile.query.filter_by(user_id=driver_user.id).first()
        assert driver_profile is not None
        assert driver_profile.availability_status == 'AVAILABLE'

def test_update_availability_with_location_success(client, driver_auth_headers, init_database):
    """Test successful update of driver availability status and location."""
    headers = driver_auth_headers
    payload = {
        'availability_status': 'AVAILABLE',
        'latitude': 12.3456,
        'longitude': 78.9101
    }

    response = client.patch('/api/drivers/availability', headers=headers, json=payload)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['message'] == 'Driver availability updated successfully.'
    assert json_data['new_status'] == 'AVAILABLE'

    # Verify in DB
    with client.application.app_context():
        driver_user = User.query.filter_by(email='driver@example.com').first()
        driver_profile = DriverProfile.query.filter_by(user_id=driver_user.id).first()
        assert driver_profile is not None
        assert driver_profile.availability_status == 'AVAILABLE'
        assert driver_profile.current_latitude == 12.3456
        assert driver_profile.current_longitude == 78.9101
        assert driver_profile.last_location_update is not None

def test_update_availability_invalid_status(client, driver_auth_headers, init_database):
    """Test updating availability with an invalid status string."""
    headers = driver_auth_headers
    payload = {'availability_status': 'INVALID_STATUS_XYZ'}

    response = client.patch('/api/drivers/availability', headers=headers, json=payload)
    assert response.status_code == 400
    json_data = response.get_json()
    assert 'Invalid availability status' in json_data['message']

def test_update_availability_not_a_driver(client, new_user_data, init_database):
    """Test a non-driver user attempting to update availability."""
    # Register and log in a regular user (not a driver)
    client.post('/api/auth/register', json=new_user_data)
    login_payload = {'email': new_user_data['email'], 'password': new_user_data['password']}
    login_response = client.post('/api/auth/login', json=login_payload)
    token = login_response.get_json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    payload = {'availability_status': 'AVAILABLE'}
    response = client.patch('/api/drivers/availability', headers=headers, json=payload)
    assert response.status_code == 404 # Expect Driver profile not found
    json_data = response.get_json()
    assert json_data['message'] == 'Driver profile not found for this user.'

def test_update_availability_missing_status_payload(client, driver_auth_headers, init_database):
    """Test updating availability without the status in payload."""
    headers = driver_auth_headers
    payload = {'latitude': 12.34} # Missing availability_status

    response = client.patch('/api/drivers/availability', headers=headers, json=payload)
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['message'] == 'Availability status is required in the request body.'

def test_update_availability_unauthenticated(client, init_database):
    """Test updating availability without authentication."""
    payload = {'availability_status': 'AVAILABLE'}
    response = client.patch('/api/drivers/availability', json=payload)
    assert response.status_code == 401 # Expect Unauthorized
    json_data = response.get_json()
    assert 'token is missing' in json_data.get('message', '').lower() or \
           'authorization header is missing' in json_data.get('message', '').lower() # Accommodate different possible messages
