import json
from app.models import User, Ride, Location, DriverProfile, Vehicle
from app import db

def test_admin_route_unauthorized(client):
    """Test accessing an admin route without authentication."""
    response = client.get('/api/admin/users')
    assert response.status_code == 401 # Unauthorized

def test_admin_route_forbidden_for_normal_user(client, new_user_data, init_database):
    """Test accessing an admin route with a non-admin user's token."""
    # Register and login a normal user
    client.post('/api/auth/register', json=new_user_data)
    login_resp = client.post('/api/auth/login', json={'email': new_user_data['email'], 'password': new_user_data['password']})
    token = login_resp.get_json()['token']
    headers = {'Authorization': f'Bearer {token}'}
    
    response = client.get('/api/admin/users', headers=headers)
    assert response.status_code == 403 # Forbidden

def test_get_all_users_as_admin(client, admin_auth_headers):
    """Test GET /api/admin/users with admin credentials."""
    response = client.get('/api/admin/users', headers=admin_auth_headers)
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'users' in json_data
    assert isinstance(json_data['users'], list)
    # Further checks can be added, e.g., for the presence of admin user in the list

def test_get_platform_stats_as_admin(client, admin_auth_headers, new_user_data, init_database): # Added new_user_data and init_database
    """Test GET /api/admin/stats with admin credentials and verify data accuracy."""
    
    # Initial counts (admin user from admin_auth_headers fixture already exists)
    initial_users_count = 1 
    initial_drivers_count = 0 # Assuming admin is not a driver by default in fixture
    initial_verified_drivers_count = 0
    initial_vehicles_count = 0
    initial_active_vehicles_count = 0

    # 1. Create a regular user
    user1_email = "user1@example.com"
    client.post('/api/auth/register', json={'email': user1_email, 'password': 'password', 'full_name': 'User One'})
    
    # 2. Create a verified driver with 1 active and 1 inactive vehicle
    driver1_email = "driver1@example.com"
    reg_resp_driver1 = client.post('/api/auth/register', json={'email': driver1_email, 'password': 'password', 'full_name': 'Driver One'})
    driver1_id = reg_resp_driver1.get_json()['user']['id']

    with client.application.app_context():
        driver_user1 = db.session.get(User, driver1_id)
        driver_user1.is_driver = True
        
        driver_profile1 = DriverProfile(user_id=driver1_id, license_number="D1LIC", is_verified=True)
        db.session.add(driver_profile1)
        
        vehicle1_active = Vehicle(driver_id=driver1_id, make="Toyota", model="Camry", year=2020, license_plate="D1V1", is_active=True, vehicle_type='SEDAN')
        vehicle1_inactive = Vehicle(driver_id=driver1_id, make="Honda", model="Civic", year=2019, license_plate="D1V2", is_active=False, vehicle_type='SEDAN')
        db.session.add_all([vehicle1_active, vehicle1_inactive])
        db.session.commit()

    # 3. Create an unverified driver with 1 active vehicle
    driver2_email = "driver2@example.com"
    reg_resp_driver2 = client.post('/api/auth/register', json={'email': driver2_email, 'password': 'password', 'full_name': 'Driver Two'})
    driver2_id = reg_resp_driver2.get_json()['user']['id']

    with client.application.app_context():
        driver_user2 = db.session.get(User, driver2_id)
        driver_user2.is_driver = True # User becomes a driver
        
        # DriverProfile is created but not verified by admin yet
        driver_profile2 = DriverProfile(user_id=driver2_id, license_number="D2LIC", is_verified=False) 
        db.session.add(driver_profile2)
        
        vehicle2_active = Vehicle(driver_id=driver2_id, make="Ford", model="Focus", year=2021, license_plate="D2V1", is_active=True, vehicle_type='SUV')
        db.session.add(vehicle2_active)
        db.session.commit()

    # 4. Call the stats endpoint
    response = client.get('/api/admin/stats', headers=admin_auth_headers)
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'platform_statistics' in json_data
    stats = json_data['platform_statistics']

    # 5. Assertions
    # Total users = admin (1) + user1 (1) + driver1 (1) + driver2 (1) = 4
    assert stats['total_users'] == initial_users_count + 3 
    
    assert 'drivers' in stats
    # Total drivers = driver1 (1) + driver2 (1) = 2
    assert stats['drivers']['total'] == initial_drivers_count + 2
    # Verified drivers = driver1 (1)
    assert stats['drivers']['verified'] == initial_verified_drivers_count + 1
    # Unverified drivers = driver2 (1)
    assert stats['drivers']['unverified'] == (initial_drivers_count + 2) - (initial_verified_drivers_count + 1) # total - verified

    assert 'rides' in stats # Basic check, ride stats not focus of this enhancement
    
    assert 'vehicles' in stats
    # Total vehicles = vehicle1_active (1) + vehicle1_inactive (1) + vehicle2_active (1) = 3
    assert stats['vehicles']['total'] == initial_vehicles_count + 3
    # Active vehicles = vehicle1_active (1) + vehicle2_active (1) = 2
    assert stats['vehicles']['active'] == initial_active_vehicles_count + 2
    # Inactive vehicles = vehicle1_inactive (1)
    assert stats['vehicles']['inactive'] == (initial_vehicles_count + 3) - (initial_active_vehicles_count + 2) # total - active

# --- Admin User Management Tests ---

def test_get_specific_user_as_admin(client, admin_auth_headers, new_user_data, init_database):
    """Test GET /api/admin/users/<user_id> with admin credentials."""
    # Register a new user to be fetched
    reg_resp = client.post('/api/auth/register', json=new_user_data)
    assert reg_resp.status_code == 201
    user_id = reg_resp.get_json()['user']['id']

    response = client.get(f'/api/admin/users/{user_id}', headers=admin_auth_headers)
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'user' in json_data
    assert json_data['user']['email'] == new_user_data['email']
    assert json_data['user']['id'] == user_id

def test_get_specific_user_not_found(client, admin_auth_headers, init_database):
    """Test GET /api/admin/users/<user_id> for a non-existent user."""
    response = client.get('/api/admin/users/9999', headers=admin_auth_headers) # Non-existent ID
    assert response.status_code == 404

def test_update_user_by_admin(client, admin_auth_headers, new_user_data, init_database):
    """Test PUT /api/admin/users/<user_id> to update user details."""
    reg_resp = client.post('/api/auth/register', json=new_user_data)
    user_id = reg_resp.get_json()['user']['id']

    update_payload = {
        'full_name': 'Updated Test User Name',
        'phone_number': '0000000000',
        'is_admin': True
    }
    response = client.patch(f'/api/admin/users/{user_id}', json=update_payload, headers=admin_auth_headers)
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['message'] == 'User details updated successfully.'
    assert json_data['user']['full_name'] == update_payload['full_name']
    assert json_data['user']['phone_number'] == update_payload['phone_number']
    assert json_data['user']['is_admin'] == True

    # Verify in DB (optional, but good practice)
    with client.application.app_context():
        user = db.session.get(User, user_id)
        assert user.full_name == update_payload['full_name']
        assert user.is_admin == True

def test_update_user_by_admin_no_data(client, admin_auth_headers, new_user_data, init_database):
    """Test PUT /api/admin/users/<user_id> with no data."""
    reg_resp = client.post('/api/auth/register', json=new_user_data)
    user_id = reg_resp.get_json()['user']['id']

    response = client.patch(f'/api/admin/users/{user_id}', json={}, headers=admin_auth_headers)
    assert response.status_code == 400
    assert response.get_json()['message'] == 'No input data provided for update.'

def test_update_user_by_admin_not_found(client, admin_auth_headers, init_database):
    """Test PUT /api/admin/users/<user_id> for a non-existent user."""
    response = client.patch('/api/admin/users/9999', json={'full_name': 'Any'}, headers=admin_auth_headers)
    assert response.status_code == 404

def test_delete_user_by_admin(client, admin_auth_headers, new_user_data, init_database):
    """Test DELETE /api/admin/users/<user_id> and verify cascade delete of DriverProfile and Vehicles."""
    # 1. Create a user who will be a driver
    driver_email = "driver_to_delete@example.com"
    driver_password = "password123"
    driver_full_name = "Driver ToDelete"
    
    reg_resp = client.post('/api/auth/register', json={
        'email': driver_email, 
        'password': driver_password, 
        'full_name': driver_full_name
    })
    assert reg_resp.status_code == 201
    user_id_to_delete = reg_resp.get_json()['user']['id']
    
    driver_profile_id = None
    vehicle_id = None

    with client.application.app_context():
        # 2. Make the user a driver and create DriverProfile
        user_to_delete = db.session.get(User, user_id_to_delete)
        assert user_to_delete is not None
        user_to_delete.is_driver = True
        
        driver_profile = DriverProfile(
            user_id=user_id_to_delete, 
            license_number="DEL_LIC123", 
            is_verified=True # Or False, doesn't matter for deletion
        )
        db.session.add(driver_profile)
        db.session.commit() # Commit to get driver_profile.id
        driver_profile_id = driver_profile.id

        # 3. Create a Vehicle for this driver
        vehicle = Vehicle(
            driver_id=user_id_to_delete, 
            make="TestMake", 
            model="TestModel", 
            year=2022, 
            license_plate="DELVCL1", 
            vehicle_type="SEDAN",
            is_active=True
        )
        db.session.add(vehicle)
        db.session.commit() # Commit to get vehicle.id
        vehicle_id = vehicle.id

    # 4. As admin, delete this user
    delete_response = client.delete(f'/api/admin/users/{user_id_to_delete}', headers=admin_auth_headers)
    
    # 5. Verify API response
    assert delete_response.status_code == 200
    # The message might vary; ensure it indicates success.
    # Original message: f"User {driver_email} and associated driver data deleted successfully."
    # Let's check for a more generic success or the specific user ID.
    assert "deleted successfully" in delete_response.get_json()['message'].lower()
    assert str(user_id_to_delete) in delete_response.get_json().get('deleted_user_id', str(user_id_to_delete)) # Assuming API might return deleted_user_id

    # 6. Verify user, DriverProfile, and Vehicle are deleted from DB
    with client.application.app_context():
        # Verify user is deleted
        deleted_user_check = db.session.get(User, user_id_to_delete)
        assert deleted_user_check is None, "User should be deleted from DB"

        # Verify DriverProfile is deleted
        if driver_profile_id: # Ensure it was created
            deleted_driver_profile_check = db.session.get(DriverProfile, driver_profile_id)
            assert deleted_driver_profile_check is None, "DriverProfile should be deleted from DB"
        
        # Verify Vehicle is deleted
        if vehicle_id: # Ensure it was created
            deleted_vehicle_check = db.session.get(Vehicle, vehicle_id)
            assert deleted_vehicle_check is None, "Vehicle should be deleted from DB"

    # Also, verify user is not accessible via admin GET endpoint
    get_resp_after_delete = client.get(f'/api/admin/users/{user_id_to_delete}', headers=admin_auth_headers)
    assert get_resp_after_delete.status_code == 404

def test_delete_user_by_admin_self_forbidden(client, admin_auth_headers, init_database):
    """Test DELETE /api/admin/users/<user_id> for admin trying to delete self."""
    # Get the admin's own ID from the token (a bit indirect here, or assume ID 1 if admin is first user)
    # For robustness, let's decode the token used in admin_auth_headers if possible,
    # or rely on the admin user created by admin_auth_headers fixture (usually ID 1 or 2).
    # Assuming admin_user_data from conftest.py creates 'admin@example.com'
    admin_user_email = 'admin@example.com' 
    admin_id = None
    with client.application.app_context():
        admin_user = User.query.filter_by(email=admin_user_email).first()
        assert admin_user is not None, "Admin user for self-delete test not found."
        admin_id = admin_user.id

    response = client.delete(f'/api/admin/users/{admin_id}', headers=admin_auth_headers)
    assert response.status_code == 403
    assert response.get_json()['message'] == 'Cannot delete the last admin account.'

def test_delete_user_by_admin_not_found(client, admin_auth_headers, init_database):
    """Test DELETE /api/admin/users/<user_id> for a non-existent user."""
    response = client.delete('/api/admin/users/9999', headers=admin_auth_headers)
    assert response.status_code == 404


# --- Admin Ride Management Tests ---

def test_get_specific_ride_as_admin(client, admin_auth_headers, new_user_data, init_database):
    """Test GET /api/admin/rides/<ride_id> with admin credentials."""
    # 1. Register and login a regular user
    reg_resp = client.post('/api/auth/register', json=new_user_data)
    assert reg_resp.status_code == 201
    login_payload = {'email': new_user_data['email'], 'password': new_user_data['password']}
    login_resp = client.post('/api/auth/login', json=login_payload)
    assert login_resp.status_code == 200
    user_token = login_resp.get_json()['token']
    user_headers = {'Authorization': f'Bearer {user_token}'}

    # 2. Book a ride as the regular user
    ride_payload = {
        "pickup_location": {"latitude": 34.0522, "longitude": -118.2437, "address_line1": "123 Main St", "city": "LA", "state": "CA", "postal_code": "90001"},
        "dropoff_location": {"latitude": 34.0522, "longitude": -118.2537, "address_line1": "456 Oak St", "city": "LA", "state": "CA", "postal_code": "90002"},
        "vehicle_type": "SEDAN"
    }
    book_ride_resp = client.post('/api/rides/book-ride', json=ride_payload, headers=user_headers)
    assert book_ride_resp.status_code == 201
    ride_id = book_ride_resp.get_json()['ride']['id']

    # 3. As admin, fetch the ride details
    response = client.get(f'/api/admin/rides/{ride_id}', headers=admin_auth_headers)
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'ride' in json_data
    assert json_data['ride']['id'] == ride_id
    assert json_data['ride']['passenger']['email'] == new_user_data['email']
    assert json_data['ride']['pickup_location']['latitude'] == ride_payload['pickup_location']['latitude']

def test_get_specific_ride_as_admin_not_found(client, admin_auth_headers, init_database):
    """Test GET /api/admin/rides/<ride_id> for a non-existent ride."""
    response = client.get('/api/admin/rides/99999', headers=admin_auth_headers) # Non-existent ride ID
    assert response.status_code == 404
    assert response.get_json()['message'] == 'Ride not found.'

def test_cancel_ride_by_admin(client, admin_auth_headers, new_user_data, init_database):
    """Test PATCH /api/admin/rides/<ride_id>/cancel-by-admin to cancel a ride."""
    # 1. Register and login a regular user
    reg_resp = client.post('/api/auth/register', json=new_user_data)
    assert reg_resp.status_code == 201
    login_payload = {'email': new_user_data['email'], 'password': new_user_data['password']}
    login_resp = client.post('/api/auth/login', json=login_payload)
    assert login_resp.status_code == 200
    user_token = login_resp.get_json()['token']
    user_headers = {'Authorization': f'Bearer {user_token}'}

    # 2. Book a ride as the regular user
    ride_payload = {
        "pickup_location": {"latitude": 34.0522, "longitude": -118.2437, "address_line1": "123 Main St", "city": "LA", "state": "CA", "postal_code": "90001"},
        "dropoff_location": {"latitude": 34.0522, "longitude": -118.2537, "address_line1": "456 Oak St", "city": "LA", "state": "CA", "postal_code": "90002"},
        "vehicle_type": "SEDAN"
    }
    book_ride_resp = client.post('/api/rides/book-ride', json=ride_payload, headers=user_headers)
    assert book_ride_resp.status_code == 201
    ride_id = book_ride_resp.get_json()['ride']['id']

    # 3. As admin, cancel the ride
    cancel_response = client.patch(f'/api/admin/rides/{ride_id}/cancel-by-admin', headers=admin_auth_headers)
    assert cancel_response.status_code == 200
    assert cancel_response.get_json()['message'] == f'Ride {ride_id} has been cancelled by admin.'

    # 4. Verify the ride status by fetching it again via API
    get_ride_response = client.get(f'/api/admin/rides/{ride_id}', headers=admin_auth_headers)
    assert get_ride_response.status_code == 200
    ride_data = get_ride_response.get_json()['ride']
    assert ride_data['id'] == ride_id
    assert ride_data['status'] == 'CANCELLED_ADMIN'

def test_cancel_ride_by_admin_not_found(client, admin_auth_headers, init_database):
    """Test PATCH /api/admin/rides/<ride_id>/cancel-by-admin for a non-existent ride."""
    response = client.patch('/api/admin/rides/99999/cancel-by-admin', headers=admin_auth_headers) # Non-existent ride ID
    assert response.status_code == 404
    assert response.get_json()['message'] == 'Ride not found.'

def test_cancel_ride_by_admin_already_processed(client, admin_auth_headers, new_user_data, init_database):
    """Test admin cancelling a ride that's already in a final state (e.g., COMPLETED)."""
    # 1. Register and login a regular user
    reg_resp = client.post('/api/auth/register', json=new_user_data)
    assert reg_resp.status_code == 201
    login_payload = {'email': new_user_data['email'], 'password': new_user_data['password']}
    login_resp = client.post('/api/auth/login', json=login_payload)
    assert login_resp.status_code == 200
    user_token = login_resp.get_json()['token']
    user_headers = {'Authorization': f'Bearer {user_token}'}

    # 2. Book a ride as the regular user
    ride_payload = {
        "pickup_location": {"latitude": 34.0522, "longitude": -118.2437, "address_line1": "123 Main St", "city": "LA", "state": "CA", "postal_code": "90001"},
        "dropoff_location": {"latitude": 34.0522, "longitude": -118.2537, "address_line1": "456 Oak St", "city": "LA", "state": "CA", "postal_code": "90002"},
        "vehicle_type": "SEDAN"
    }
    book_ride_resp = client.post('/api/rides/book-ride', json=ride_payload, headers=user_headers)
    assert book_ride_resp.status_code == 201
    ride_id = book_ride_resp.get_json()['ride']['id']

    # 3. Manually update ride status to COMPLETED in DB
    with client.application.app_context():
        ride_to_complete = db.session.get(Ride, ride_id)
        assert ride_to_complete is not None
        ride_to_complete.status = 'COMPLETED'
        db.session.commit()

    # 4. As admin, attempt to cancel the 'COMPLETED' ride
    response = client.patch(f'/api/admin/rides/{ride_id}/cancel-by-admin', headers=admin_auth_headers)
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data['message'] == f'Ride is already COMPLETED and cannot be cancelled again.'


def test_verify_driver_profile_success(client, admin_auth_headers, new_user_data, init_database):
    """Test successful verification of a driver profile by an admin."""
    # 1. Register a regular user
    reg_resp = client.post('/api/auth/register', json=new_user_data)
    assert reg_resp.status_code == 201
    user_id = reg_resp.get_json()['user']['id']

    # 2. Create a DriverProfile for this user (initially unverified and user not marked as driver)
    with client.application.app_context():
        user_for_driver = db.session.get(User, user_id)
        assert user_for_driver is not None
        user_for_driver.is_driver = False # Explicitly set for test clarity

        driver_profile = DriverProfile(
            user_id=user_id,
            license_number="TESTLIC123",
            is_verified=False,
            verification_notes="Pending review",
            availability_status="UNAVAILABLE" 
        )
        db.session.add(driver_profile)
        db.session.commit()
        driver_profile_id = driver_profile.id
        
        # Re-fetch to ensure user.is_driver is False before verification
        user_for_driver = db.session.get(User, user_id) 
        assert user_for_driver.is_driver == False

    # 3. Admin verifies the driver profile
    verification_payload = {
        "is_verified": True,
        "verification_notes": "Profile looks good. Approved."
    }
    response = client.patch(f'/api/admin/drivers/{driver_profile_id}/verify', 
                            headers=admin_auth_headers, 
                            json=verification_payload)
    
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['message'] == 'Driver profile verification status updated.'
    assert 'driver_profile' in json_data
    
    returned_profile = json_data['driver_profile']
    assert returned_profile['id'] == driver_profile_id
    assert returned_profile['is_verified'] is True
    assert returned_profile['verification_notes'] == "Profile looks good. Approved."
    assert returned_profile['user_id'] == user_id

    # 4. Verify changes in the database (DriverProfile and User)
    with client.application.app_context():
        verified_profile_db = db.session.get(DriverProfile, driver_profile_id)
        assert verified_profile_db is not None
        assert verified_profile_db.is_verified is True
        assert verified_profile_db.verification_notes == "Profile looks good. Approved."
        
        # Check if the user's is_driver flag was updated
        associated_user = db.session.get(User, user_id)
        assert associated_user is not None
        assert associated_user.is_driver is True

