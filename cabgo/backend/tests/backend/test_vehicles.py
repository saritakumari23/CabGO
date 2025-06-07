

import pytest
import json
from app import db
from app.models import User, DriverProfile, Vehicle

@pytest.fixture(scope='function')
def verified_driver_user_data():
    """Provides data for a new user who will become a verified driver."""
    return {
        'email': 'verified_driver@example.com',
        'password': 'verifypassword',
        'full_name': 'Verified Driver',
        'phone_number': '5566778899',
        'is_admin': False
    }

@pytest.fixture(scope='function')
def verified_driver_auth_headers(client, verified_driver_user_data, init_database):
    """Registers a user, makes them a VERIFIED driver, logs them in, and returns auth headers."""
    # Register the user
    registration_payload = {k: v for k, v in verified_driver_user_data.items() if k != 'is_admin'}
    reg_response = client.post('/api/auth/register', json=registration_payload)
    assert reg_response.status_code == 201
    user_id = reg_response.get_json()['user']['id']

    # Create and VERIFY a DriverProfile for this user
    with client.application.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        user.is_driver = True # Mark as driver

        driver_profile = DriverProfile(
            user_id=user.id,
            license_number=f'VERIFIEDLIC{user.id}', # Unique license
            availability_status='OFFLINE', # Initial status
            is_verified=True # Key difference: driver is verified
        )
        db.session.add(user)
        db.session.add(driver_profile)
        db.session.commit()

    # Log in as this new verified driver user
    login_payload = {'email': verified_driver_user_data['email'], 'password': verified_driver_user_data['password']}
    login_response = client.post('/api/auth/login', json=login_payload)
    assert login_response.status_code == 200
    token = login_response.get_json().get('token')
    assert token is not None

    return {'Authorization': f'Bearer {token}'}

@pytest.fixture(scope='function')
def unverified_driver_user_data():
    """Provides data for a new user who will be an unverified driver."""
    return {
        'email': 'unverified_driver@example.com',
        'password': 'unverifypass',
        'full_name': 'Unverified Driver',
        'phone_number': '5544332211',
        'is_admin': False
    }

@pytest.fixture(scope='function')
def unverified_driver_auth_headers(client, unverified_driver_user_data, init_database):
    """Registers a user, makes them an UNVERIFIED driver, logs them in, and returns auth headers."""
    registration_payload = {k: v for k, v in unverified_driver_user_data.items() if k != 'is_admin'}
    reg_response = client.post('/api/auth/register', json=registration_payload)
    assert reg_response.status_code == 201
    user_id = reg_response.get_json()['user']['id']

    with client.application.app_context():
        user = db.session.get(User, user_id)
        assert user is not None
        user.is_driver = True

        driver_profile = DriverProfile(
            user_id=user.id,
            license_number=f'UNVERIFIEDLIC{user.id}',
            availability_status='OFFLINE',
            is_verified=False # Key: driver is NOT verified
        )
        db.session.add(user)
        db.session.add(driver_profile)
        db.session.commit()

    login_payload = {'email': unverified_driver_user_data['email'], 'password': unverified_driver_user_data['password']}
    login_response = client.post('/api/auth/login', json=login_payload)
    assert login_response.status_code == 200
    token = login_response.get_json().get('token')
    assert token is not None

    return {'Authorization': f'Bearer {token}'}

def test_add_vehicle_success(client, verified_driver_auth_headers, init_database):
    """Test successful vehicle addition by a verified driver."""
    headers = verified_driver_auth_headers
    vehicle_payload = {
        'make': 'Toyota',
        'model': 'Camry',
        'year': 2021,
        'color': 'Silver',
        'license_plate': 'TESTCAR123',
        'vehicle_type': 'SEDAN'
    }
    response = client.post('/api/vehicles/add', headers=headers, json=vehicle_payload)
    assert response.status_code == 201
    json_data = response.get_json()
    assert json_data['message'] == 'Vehicle added successfully.'
    assert 'vehicle' in json_data
    assert json_data['vehicle']['license_plate'] == 'TESTCAR123'
    assert json_data['vehicle']['make'] == 'Toyota'
    assert json_data['vehicle']['vehicle_type'] == 'SEDAN'
    assert json_data['vehicle']['is_active'] is True # Default

    # Verify in DB
    with client.application.app_context():
        vehicle = Vehicle.query.filter_by(license_plate='TESTCAR123').first()
        assert vehicle is not None
        assert vehicle.make == 'Toyota'
        driver_user = User.query.filter_by(email='verified_driver@example.com').first()
        assert vehicle.driver_id == driver_user.id

def test_add_vehicle_not_a_driver(client, new_user_data, init_database):
    """Test a non-driver user attempting to add a vehicle."""
    # Register and log in a regular user (not a driver)
    client.post('/api/auth/register', json=new_user_data)
    login_payload = {'email': new_user_data['email'], 'password': new_user_data['password']}
    login_response = client.post('/api/auth/login', json=login_payload)
    token = login_response.get_json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    vehicle_payload = {'make': 'Honda', 'model': 'Civic', 'license_plate': 'NODRIVER', 'vehicle_type': 'SEDAN'}
    response = client.post('/api/vehicles/add', headers=headers, json=vehicle_payload)
    assert response.status_code == 403
    assert response.get_json()['message'] == 'Only registered drivers can add vehicles.'

def test_add_vehicle_unverified_driver(client, unverified_driver_auth_headers, init_database):
    """Test an unverified driver attempting to add a vehicle."""
    headers = unverified_driver_auth_headers
    vehicle_payload = {'make': 'Ford', 'model': 'Focus', 'license_plate': 'UNVERIFIED', 'vehicle_type': 'HATCHBACK'}
    response = client.post('/api/vehicles/add', headers=headers, json=vehicle_payload)
    assert response.status_code == 403
    assert response.get_json()['message'] == 'Driver profile not found or not verified. Cannot add vehicle.'
def test_add_vehicle_missing_fields(client, verified_driver_auth_headers, init_database):
    """Test adding a vehicle with missing required fields."""
    headers = verified_driver_auth_headers
    # Missing 'license_plate' and 'vehicle_type'
    vehicle_payload = {'make': 'Kia', 'model': 'Seltos'}
    response = client.post('/api/vehicles/add', headers=headers, json=vehicle_payload)
    assert response.status_code == 400
    # The endpoint checks fields in a specific order, so we test for the first one it would find missing.
    # Based on current app/vehicles.py: 'make', 'model', 'license_plate', 'vehicle_type'
    assert 'License plate is required' in response.get_json()['message'] 

def test_add_vehicle_invalid_vehicle_type(client, verified_driver_auth_headers, init_database):
    """Test adding a vehicle with an invalid vehicle_type."""
    headers = verified_driver_auth_headers
    vehicle_payload = {
        'make': 'Tesla', 'model': 'Model S', 'license_plate': 'INVALIDVT', 'vehicle_type': 'SPACESHIP'
    }
    response = client.post('/api/vehicles/add', headers=headers, json=vehicle_payload)
    assert response.status_code == 400
    json_data = response.get_json()
    assert 'Invalid vehicle type' in json_data['message']
    valid_types = [choice[0] for choice in Vehicle.vehicle_type_choices]
    assert str(valid_types) in json_data['message']

def test_add_vehicle_duplicate_license_plate(client, verified_driver_auth_headers, init_database):
    """Test adding a vehicle with a duplicate license_plate."""
    headers = verified_driver_auth_headers
    vehicle_payload1 = {
        'make': 'Nissan', 'model': 'Rogue', 'license_plate': 'DUPLICATELP', 'vehicle_type': 'SUV'
    }
    # Add first vehicle
    response1 = client.post('/api/vehicles/add', headers=headers, json=vehicle_payload1)
    assert response1.status_code == 201

    # Attempt to add another vehicle with the same license plate
    vehicle_payload2 = {
        'make': 'Subaru', 'model': 'Forester', 'license_plate': 'DUPLICATELP', 'vehicle_type': 'SUV'
    }
    response2 = client.post('/api/vehicles/add', headers=headers, json=vehicle_payload2)
    assert response2.status_code == 409 # Conflict
    assert response2.get_json()['message'] == 'This license plate is already registered.'

def test_add_vehicle_unauthenticated(client, init_database):
    """Test adding a vehicle without authentication."""
    vehicle_payload = {'make': 'Mazda', 'model': 'CX-5', 'license_plate': 'NOAUTH', 'vehicle_type': 'SUV'}
    response = client.post('/api/vehicles/add', json=vehicle_payload)
    assert response.status_code == 401
    json_data = response.get_json()
    assert 'token is missing' in json_data.get('message', '').lower() or \
           'authorization header is missing' in json_data.get('message', '').lower()

def test_list_driver_vehicles_success(client, verified_driver_auth_headers, init_database):
    """Test successfully listing vehicles for a driver with vehicles."""
    headers = verified_driver_auth_headers

    # Add a couple of vehicles for this driver first
    vehicle_payload1 = {
        'make': 'Honda', 'model': 'CRV', 'license_plate': 'DRIVERVEH1', 'vehicle_type': 'SUV'
    }
    response1 = client.post('/api/vehicles/add', headers=headers, json=vehicle_payload1)
    assert response1.status_code == 201
    vehicle_id1 = response1.get_json()['vehicle']['id']

    vehicle_payload2 = {
        'make': 'Mazda', 'model': '3', 'license_plate': 'DRIVERVEH2', 'vehicle_type': 'SEDAN'
    }
    response2 = client.post('/api/vehicles/add', headers=headers, json=vehicle_payload2)
    assert response2.status_code == 201

    # Now list the vehicles
    list_response = client.get('/api/vehicles', headers=headers)
    assert list_response.status_code == 200
    json_data = list_response.get_json()
    assert 'vehicles' in json_data
    assert len(json_data['vehicles']) == 2
    license_plates = {v['license_plate'] for v in json_data['vehicles']}
    assert 'DRIVERVEH1' in license_plates
    assert 'DRIVERVEH2' in license_plates
    # Check for one vehicle's details
    vehicle1_data = next(v for v in json_data['vehicles'] if v['id'] == vehicle_id1)
    assert vehicle1_data['make'] == 'Honda'
    assert vehicle1_data['model'] == 'CRV'
    assert vehicle1_data['vehicle_type'] == 'SUV'
    assert 'created_at' in vehicle1_data
    assert 'updated_at' in vehicle1_data

def test_list_driver_vehicles_no_vehicles(client, verified_driver_auth_headers, init_database):
    """Test listing vehicles for a driver who has no vehicles."""
    headers = verified_driver_auth_headers
    # This driver (from verified_driver_auth_headers) has not added any vehicles in this test yet

    response = client.get('/api/vehicles', headers=headers)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['message'] == 'No vehicles found for this driver.'
    assert 'vehicles' in json_data
    assert len(json_data['vehicles']) == 0

def test_list_driver_vehicles_not_a_driver(client, new_user_data, init_database):
    """Test a non-driver user attempting to list vehicles."""
    # Register and log in a regular user
    client.post('/api/auth/register', json=new_user_data)
    login_payload = {'email': new_user_data['email'], 'password': new_user_data['password']}
    login_response = client.post('/api/auth/login', json=login_payload)
    token = login_response.get_json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    response = client.get('/api/vehicles', headers=headers)
    assert response.status_code == 403
    assert response.get_json()['message'] == 'Only drivers can view their vehicles.'

def test_list_driver_vehicles_unauthenticated(client, init_database):
    """Test listing vehicles without authentication."""
    response = client.get('/api/vehicles')
    assert response.status_code == 401
    json_data = response.get_json()
    assert 'token is missing' in json_data.get('message', '').lower() or \
           'authorization header is missing' in json_data.get('message', '').lower()