from flask import Blueprint, jsonify, current_app
from flask import request # Import request
import datetime # Import datetime for setting cancelled_at
from datetime import timezone # Import timezone for UTC
from .models import User, DriverProfile, Ride, Location, Vehicle
from . import db # Import db for session management
from .decorators import admin_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users', methods=['GET'])
@admin_required
def list_users(current_admin_user):
    """Lists all users in the system. Accessible only by admins."""
    try:
        users = User.query.all()
        users_data = []
        for user in users:
            user_info = {
                'id': user.id,
                'email': user.email,
                'full_name': user.full_name,
                'phone_number': user.phone_number,
                'is_driver': user.is_driver,
                'is_admin': user.is_admin,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'updated_at': user.updated_at.isoformat() if user.updated_at else None
            }
            # Add driver profile info if user is a driver
            if user.is_driver and hasattr(user, 'driver_profile') and user.driver_profile:
                user_info['driver_profile'] = {
                    'id': user.driver_profile.id,
                    'license_number': user.driver_profile.license_number,
                    'is_verified': user.driver_profile.is_verified,
                    'availability_status': user.driver_profile.availability_status
                }
            users_data.append(user_info)
        
        return jsonify({'users': users_data}), 200

    except Exception as e:
        current_app.logger.error(f"Error listing users (admin): {e}")
        return jsonify({'message': 'Failed to list users due to an internal error'}), 500

@admin_bp.route('/drivers/<int:driver_profile_id>/verify', methods=['PATCH'])
@admin_required
def verify_driver_profile(current_admin_user, driver_profile_id):
    """Allows an admin to verify a driver's profile and add notes."""
    try:
        driver_profile = db.session.get(DriverProfile, driver_profile_id)
        if not driver_profile:
            return jsonify({'message': 'Driver profile not found.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'message': 'No input data provided for verification.'}), 400

        # Update verification status
        if 'is_verified' in data:
            if not isinstance(data['is_verified'], bool):
                return jsonify({'message': 'is_verified must be a boolean.'}), 400
            driver_profile.is_verified = data['is_verified']
        
        # Update verification notes
        if 'verification_notes' in data:
            driver_profile.verification_notes = str(data['verification_notes'])
        
        # If verifying, ensure the associated User's is_driver flag is True
        # (It should have been set during driver registration, but this is a safeguard)
        if driver_profile.is_verified and driver_profile.user:
            if not driver_profile.user.is_driver:
                driver_profile.user.is_driver = True
                db.session.add(driver_profile.user) # Add user to session if modified

        db.session.add(driver_profile)
        db.session.commit()

        profile_data = {
            'id': driver_profile.id,
            'user_id': driver_profile.user_id,
            'license_number': driver_profile.license_number,
            'is_verified': driver_profile.is_verified,
            'verification_notes': driver_profile.verification_notes,
            'availability_status': driver_profile.availability_status,
            'user_full_name': driver_profile.user.full_name if driver_profile.user else None
        }
        return jsonify({'message': 'Driver profile verification status updated.', 'driver_profile': profile_data}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error verifying driver profile {driver_profile_id} (admin): {e}")
        return jsonify({'message': 'Failed to update driver profile verification due to an internal error'}), 500

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_details(current_admin_user, user_id):
    """Gets detailed information for a specific user. Accessible only by admins."""
    try:
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({'message': 'User not found.'}), 404

        user_info = {
            'id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            'phone_number': user.phone_number,
            'is_driver': user.is_driver,
            'is_admin': user.is_admin,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None
        }
        if user.is_driver and hasattr(user, 'driver_profile') and user.driver_profile:
            user_info['driver_profile'] = {
                'id': user.driver_profile.id,
                'license_number': user.driver_profile.license_number,
                'is_verified': user.driver_profile.is_verified,
                'availability_status': user.driver_profile.availability_status,
                'license_expiry_date': user.driver_profile.license_expiry_date.isoformat() if user.driver_profile.license_expiry_date else None,
                'verification_notes': user.driver_profile.verification_notes
            }
        
        # Include vehicles if the user is a driver
        if user.is_driver and hasattr(user, 'vehicles'):
            user_info['vehicles'] = [
                {
                    'id': v.id,
                    'make': v.make,
                    'model': v.model,
                    'license_plate': v.license_plate,
                    'vehicle_type': v.vehicle_type,
                    'is_active': v.is_active
                } for v in user.vehicles
            ]

        return jsonify({'user': user_info}), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching user {user_id} (admin): {e}")
        return jsonify({'message': 'Failed to fetch user details due to an internal error'}), 500


@admin_bp.route('/users/<int:user_id>', methods=['PATCH'])
@admin_required
def update_user_details(current_admin_user, user_id):
    """Updates a user's details (full_name, phone_number, is_driver, is_admin). Accessible only by admins."""
    try:
        user_to_update = db.session.get(User, user_id)
        if not user_to_update:
            return jsonify({'message': 'User not found.'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'message': 'No input data provided for update.'}), 400

        if 'full_name' in data:
            user_to_update.full_name = data['full_name']
        if 'phone_number' in data:
            # Add validation for phone number format/uniqueness if necessary
            user_to_update.phone_number = data['phone_number']
        
        if 'is_driver' in data:
            if not isinstance(data['is_driver'], bool):
                return jsonify({'message': 'is_driver must be a boolean.'}), 400
            user_to_update.is_driver = data['is_driver']
            # If setting is_driver to False, consider deactivating driver_profile or vehicles - for now, just updating the flag.
            # If setting is_driver to True, this doesn't create a DriverProfile. That's a separate flow.

        if 'is_admin' in data:
            if not isinstance(data['is_admin'], bool):
                return jsonify({'message': 'is_admin must be a boolean.'}), 400
            
            # Prevent admin from removing their own admin status if they are the only admin
            if user_to_update.id == current_admin_user.id and not data['is_admin']:
                admin_count = User.query.filter_by(is_admin=True).count()
                if admin_count <= 1:
                    return jsonify({'message': 'Cannot remove the last admin\'s privileges.'}), 403
            user_to_update.is_admin = data['is_admin']

        db.session.add(user_to_update)
        db.session.commit()

        # Return updated user details (similar to get_user_details)
        updated_user_info = {
            'id': user_to_update.id,
            'email': user_to_update.email,
            'full_name': user_to_update.full_name,
            'phone_number': user_to_update.phone_number,
            'is_driver': user_to_update.is_driver,
            'is_admin': user_to_update.is_admin
        }
        return jsonify({'message': 'User details updated successfully.', 'user': updated_user_info}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user {user_id} (admin): {e}")
        return jsonify({'message': 'Failed to update user details due to an internal error'}), 500



@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(current_admin_user, user_id):
    """Deletes a user and their associated driver profile and vehicles. Blocks deletion if user has passenger ride history."""
    try:
        user_to_delete = db.session.get(User, user_id)
        if not user_to_delete:
            return jsonify({'message': 'User not found.'}), 404

        # Prevent admin from deleting themselves if they are the only admin
        if user_to_delete.id == current_admin_user.id and user_to_delete.is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count <= 1:
                return jsonify({'message': 'Cannot delete the last admin account.'}), 403

        # Check for rides as a passenger
        passenger_rides_count = Ride.query.filter_by(passenger_id=user_to_delete.id).count()
        if passenger_rides_count > 0:
            return jsonify({'message': 'Cannot delete user. User has existing ride history as a passenger. Consider deactivating the user instead.'}), 400

        # If user is a driver, handle related data
        if user_to_delete.is_driver:
            # Nullify driver_id in Rides
            rides_as_driver = Ride.query.filter_by(driver_id=user_to_delete.id).all()
            for ride in rides_as_driver:
                ride.driver_id = None
                # Optionally, update ride status if it was active (e.g., 'ACCEPTED' -> 'NO_DRIVERS_FOUND')
                # For simplicity, just nullifying driver_id for now.
                db.session.add(ride)

            # Delete Vehicles associated with the user
            Vehicle.query.filter_by(driver_id=user_to_delete.id).delete()
            
            # Delete DriverProfile
            if user_to_delete.driver_profile:
                db.session.delete(user_to_delete.driver_profile)
        
        db.session.delete(user_to_delete)
        db.session.commit()

        return jsonify({'message': f'User {user_to_delete.email} and associated driver data deleted successfully.'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user {user_id} (admin): {e}")
        return jsonify({'message': 'Failed to delete user due to an internal error.'}), 500


@admin_bp.route('/rides', methods=['GET'])
@admin_required
def list_all_rides(current_admin_user):
    """Lists all rides in the system. Accessible only by admins."""
    try:
        rides = Ride.query.order_by(Ride.requested_at.desc()).all()
        if not rides:
            return jsonify({'message': 'No rides found in the system.', 'rides': []}), 200

        rides_data = []
        for ride in rides:
            pickup_loc = Location.query.get(ride.pickup_location_id)
            dropoff_loc = Location.query.get(ride.dropoff_location_id)
            passenger = User.query.get(ride.passenger_id)
            driver = User.query.get(ride.driver_id) if ride.driver_id else None

            ride_info = {
                'id': ride.id,
                'status': ride.status,
                'passenger': {
                    'id': passenger.id if passenger else None,
                    'full_name': passenger.full_name if passenger else None,
                    'email': passenger.email if passenger else None
                },
                'driver': {
                    'id': driver.id if driver else None,
                    'full_name': driver.full_name if driver else None,
                    'email': driver.email if driver else None
                } if driver else None,
                'pickup_location': {
                    'latitude': pickup_loc.latitude if pickup_loc else None,
                    'longitude': pickup_loc.longitude if pickup_loc else None,
                    'address': pickup_loc.address_line1 if pickup_loc else None
                },
                'dropoff_location': {
                    'latitude': dropoff_loc.latitude if dropoff_loc else None,
                    'longitude': dropoff_loc.longitude if dropoff_loc else None,
                    'address': dropoff_loc.address_line1 if dropoff_loc else None
                },
                'requested_at': ride.requested_at.isoformat() if ride.requested_at else None,
                'accepted_at': ride.accepted_at.isoformat() if ride.accepted_at else None,
                'started_at': ride.started_at.isoformat() if ride.started_at else None,
                'completed_at': ride.completed_at.isoformat() if ride.completed_at else None,
                'cancelled_at': ride.cancelled_at.isoformat() if ride.cancelled_at else None,
                'estimated_fare': ride.estimated_fare,
                'actual_fare': ride.actual_fare,
                'payment_status': ride.payment_status,
                'vehicle_type_requested': ride.vehicle_type_requested
            }
            rides_data.append(ride_info)
        
        return jsonify({'rides': rides_data}), 200

    except Exception as e:
        current_app.logger.error(f"Error listing all rides (admin): {e}")
        return jsonify({'message': 'Failed to list rides due to an internal error'}), 500

@admin_bp.route('/rides/<int:ride_id>', methods=['GET'])
@admin_required
def get_ride_details_admin(current_admin_user, ride_id):
    """Gets detailed information for a specific ride. Accessible only by admins."""
    try:
        ride = db.session.get(Ride, ride_id) # MODIFIED
        if not ride:
            return jsonify({'message': 'Ride not found.'}), 404

        pickup_loc = db.session.get(Location, ride.pickup_location_id) # MODIFIED
        dropoff_loc = db.session.get(Location, ride.dropoff_location_id) # MODIFIED
        passenger = db.session.get(User, ride.passenger_id) # MODIFIED
        driver = db.session.get(User, ride.driver_id) if ride.driver_id else None # MODIFIED

        ride_info = {
            'id': ride.id,
            'status': ride.status,
            'passenger': {
                'id': passenger.id if passenger else None,
                'full_name': passenger.full_name if passenger else None,
                'email': passenger.email if passenger else None
            },
            'driver': {
                'id': driver.id if driver else None,
                'full_name': driver.full_name if driver else None,
                'email': driver.email if driver else None
            } if driver else None,
            'pickup_location': {
                'id': pickup_loc.id if pickup_loc else None,
                'latitude': pickup_loc.latitude if pickup_loc else None,
                'longitude': pickup_loc.longitude if pickup_loc else None,
                'address_line1': pickup_loc.address_line1 if pickup_loc else None,
                'city': pickup_loc.city if pickup_loc else None,
                'postal_code': pickup_loc.postal_code if pickup_loc else None
            },
            'dropoff_location': {
                'id': dropoff_loc.id if dropoff_loc else None,
                'latitude': dropoff_loc.latitude if dropoff_loc else None,
                'longitude': dropoff_loc.longitude if dropoff_loc else None,
                'address_line1': dropoff_loc.address_line1 if dropoff_loc else None,
                'city': dropoff_loc.city if dropoff_loc else None,
                'postal_code': dropoff_loc.postal_code if dropoff_loc else None
            },
            'requested_at': ride.requested_at.isoformat() if ride.requested_at else None,
            'accepted_at': ride.accepted_at.isoformat() if ride.accepted_at else None,
            'started_at': ride.started_at.isoformat() if ride.started_at else None,
            'completed_at': ride.completed_at.isoformat() if ride.completed_at else None,
            'cancelled_at': ride.cancelled_at.isoformat() if ride.cancelled_at else None,
            'estimated_fare': ride.estimated_fare,
            'actual_fare': ride.actual_fare,
            'payment_status': ride.payment_status,
            'payment_intent_id': ride.payment_intent_id,
            'vehicle_type_requested': ride.vehicle_type_requested,
            'notes_for_driver': ride.notes_for_driver
        }
        return jsonify({'ride': ride_info}), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching ride {ride_id} (admin): {e}")
        return jsonify({'message': 'Failed to fetch ride details due to an internal error'}), 500


@admin_bp.route('/rides/<int:ride_id>/cancel-by-admin', methods=['PATCH'])
@admin_required
def cancel_ride_by_admin(current_admin_user, ride_id):
    """Allows an admin to cancel any ride."""
    try:
        ride = db.session.get(Ride, ride_id)
        if not ride:
            return jsonify({'message': 'Ride not found.'}), 404

        if ride.status in ['COMPLETED', 'CANCELLED_PASSENGER', 'CANCELLED_DRIVER', 'CANCELLED_ADMIN']:
            return jsonify({'message': f'Ride is already {ride.status} and cannot be cancelled again.'}), 400

        ride.status = 'CANCELLED_ADMIN' # New status for admin cancellation
        ride.cancelled_at = datetime.datetime.now(timezone.utc)
        # Potentially add a field for cancellation_reason_admin
        
        db.session.add(ride)
        db.session.commit()

        # TODO: Notify passenger and driver if applicable

        return jsonify({'message': f'Ride {ride_id} has been cancelled by admin.'}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling ride {ride_id} by admin: {e}")
        return jsonify({'message': 'Failed to cancel ride due to an internal error.'}), 500

@admin_bp.route('/stats', methods=['GET'])
@admin_required
def get_platform_stats(current_admin_user):
    """Provides basic platform statistics. Accessible only by admins."""
    try:
        total_users = User.query.count()
        total_drivers = User.query.filter_by(is_driver=True).count()
        verified_drivers = DriverProfile.query.filter_by(is_verified=True).count()
        
        total_rides = Ride.query.count()
        rides_by_status = {}
        for status_tuple in Ride.status_choices:
            status_code = status_tuple[0]
            count = Ride.query.filter_by(status=status_code).count()
            rides_by_status[status_code.lower()] = count
            
        total_vehicles = Vehicle.query.count()
        active_vehicles = Vehicle.query.filter_by(is_active=True).count()

        stats = {
            'total_users': total_users,
            'drivers': {
                'total': total_drivers,
                'verified': verified_drivers,
                'unverified': total_drivers - verified_drivers
            },
            'rides': {
                'total': total_rides,
                'by_status': rides_by_status
            },
            'vehicles': {
                'total': total_vehicles,
                'active': active_vehicles,
                'inactive': total_vehicles - active_vehicles
            }
        }
        return jsonify({'platform_statistics': stats}), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching platform stats (admin): {e}")
        return jsonify({'message': 'Failed to fetch platform statistics due to an internal error'}), 500

# More admin routes will be added here
