from flask import Blueprint, request, jsonify, current_app
from .models import User, DriverProfile
from . import db
from .decorators import token_required
import datetime
from datetime import timezone # Import timezone

drivers_bp = Blueprint('drivers', __name__)

@drivers_bp.route('/register', methods=['POST'])
@token_required
def register_driver(current_user):
    # Check if the user is already a driver or has a pending application
    if current_user.is_driver or DriverProfile.query.filter_by(user_id=current_user.id).first():
        return jsonify({'message': 'User is already a driver or has a pending/existing driver profile.'}), 409 # Conflict

    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    license_number = data.get('license_number')
    license_expiry_date_str = data.get('license_expiry_date') # Expected format: YYYY-MM-DD

    if not license_number:
        return jsonify({'message': 'License number is required'}), 400
    
    # Optional: Validate license_expiry_date format
    license_expiry_date = None
    if license_expiry_date_str:
        try:
            license_expiry_date = datetime.datetime.strptime(license_expiry_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'message': 'Invalid date format for license expiry. Use YYYY-MM-DD.'}), 400

    # Check if license number is already registered by another driver
    if DriverProfile.query.filter_by(license_number=license_number).first():
        return jsonify({'message': 'This license number is already registered.'}), 409

    try:
        new_driver_profile = DriverProfile(
            user_id=current_user.id,
            license_number=license_number,
            license_expiry_date=license_expiry_date,
            is_verified=False, # Verification will be an admin task
            availability_status='OFFLINE' # Default status
        )
        db.session.add(new_driver_profile)
        
        # Update the user's is_driver flag
        current_user.is_driver = True
        db.session.add(current_user)
        
        db.session.commit()

        profile_data = {
            'driver_profile_id': new_driver_profile.id,
            'user_id': new_driver_profile.user_id,
            'license_number': new_driver_profile.license_number,
            'is_verified': new_driver_profile.is_verified,
            'availability_status': new_driver_profile.availability_status
        }
        return jsonify({'message': 'Driver registration successful. Awaiting verification.', 'driver_profile': profile_data}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during driver registration for user {current_user.id}: {e}")
        return jsonify({'message': 'Driver registration failed due to an internal error'}), 500

@drivers_bp.route('/available', methods=['GET'])
# @token_required # Decide if this needs authentication - passengers might call this
def list_available_drivers():
    try:
        # Find driver profiles that are 'AVAILABLE' and 'is_verified'
        # Also join with User to get user details like full_name
        available_driver_profiles = DriverProfile.query\
            .join(User, DriverProfile.user_id == User.id)\
            .filter(DriverProfile.availability_status == 'AVAILABLE', DriverProfile.is_verified == True)\
            .all()

        if not available_driver_profiles:
            return jsonify({'message': 'No drivers currently available.', 'drivers': []}), 200

        drivers_data = []
        for profile in available_driver_profiles:
            driver_info = {
                'driver_id': profile.user_id, # This is the User.id
                'driver_profile_id': profile.id,
                'full_name': profile.user.full_name, # Accessing User model through relationship
                'phone_number': profile.user.phone_number,
                'current_latitude': profile.current_latitude,
                'current_longitude': profile.current_longitude,
                # Add vehicle info if needed, might require another join or separate query
            }
            drivers_data.append(driver_info)
        
        return jsonify({'drivers': drivers_data}), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching available drivers: {e}")
        return jsonify({'message': 'Failed to fetch available drivers due to an internal error'}), 500


@drivers_bp.route('/availability', methods=['PATCH'])
@token_required
def update_driver_availability(current_user):

    driver_profile = DriverProfile.query.filter_by(user_id=current_user.id).first()
    if not driver_profile:
        return jsonify({'message': 'Driver profile not found for this user.'}), 404

    data = request.get_json()
    if not data or 'availability_status' not in data:
        return jsonify({'message': 'Availability status is required in the request body.'}), 400

    new_status = data.get('availability_status')
    valid_statuses = [choice[0] for choice in DriverProfile.availability_status_choices]
    if new_status not in valid_statuses:
        return jsonify({'message': f'Invalid availability status. Must be one of: {valid_statuses}'}), 400

    try:
        driver_profile.availability_status = new_status
        # Optionally update location if provided
        if 'latitude' in data and 'longitude' in data:
            driver_profile.current_latitude = data.get('latitude')
            driver_profile.current_longitude = data.get('longitude')
            driver_profile.last_location_update = datetime.datetime.now(timezone.utc)
        
        db.session.commit()
        return jsonify({'message': 'Driver availability updated successfully.', 
                        'driver_id': driver_profile.user_id,
                        'new_status': driver_profile.availability_status}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating driver availability for user {current_user.id}: {e}")
        return jsonify({'message': 'Failed to update availability due to an internal error'}), 500

# Other driver-related routes will be added here
