from flask import Blueprint, request, jsonify, current_app
from .models import User, Ride, Location
from . import db
from .decorators import token_required
from .utils import calculate_distance, calculate_fare
import datetime

rides_bp = Blueprint('rides', __name__)

@rides_bp.route('/book-ride', methods=['POST'])
@token_required
def book_ride(current_user):
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    # Extract location data
    pickup_data = data.get('pickup_location')
    dropoff_data = data.get('dropoff_location')

    if not pickup_data or not dropoff_data:
        return jsonify({'message': 'Pickup and dropoff locations are required'}), 400
    
    required_location_keys = ['latitude', 'longitude']
    if not all(key in pickup_data for key in required_location_keys) or \
       not all(key in dropoff_data for key in required_location_keys):
        return jsonify({'message': 'Latitude and longitude are required for both pickup and dropoff locations'}), 400

    try:
        # Create Location objects
        pickup_location = Location(
            latitude=pickup_data['latitude'],
            longitude=pickup_data['longitude'],
            address_line1=pickup_data.get('address_line1'),
            city=pickup_data.get('city'),
            state=pickup_data.get('state'),
            postal_code=pickup_data.get('postal_code')
        )
        db.session.add(pickup_location)

        dropoff_location = Location(
            latitude=dropoff_data['latitude'],
            longitude=dropoff_data['longitude'],
            address_line1=dropoff_data.get('address_line1'),
            city=dropoff_data.get('city'),
            state=dropoff_data.get('state'),
            postal_code=dropoff_data.get('postal_code')
        )
        db.session.add(dropoff_location)
        
        # Flush to get IDs for pickup and dropoff locations before creating the ride
        db.session.flush()

        vehicle_type_requested = data.get('vehicle_type', 'SEDAN') # Default to SEDAN if not provided

        # Calculate distance
        distance_km = calculate_distance(
            pickup_location.latitude,
            pickup_location.longitude,
            dropoff_location.latitude,
            dropoff_location.longitude
        )

        # Calculate estimated fare
        estimated_fare = calculate_fare(
            distance_km=distance_km, 
            vehicle_type=vehicle_type_requested
        )

        # Create Ride object
        new_ride = Ride(
            passenger_id=current_user.id,
            pickup_location_id=pickup_location.id,
            dropoff_location_id=dropoff_location.id,
            status='REQUESTED',
            vehicle_type_requested=vehicle_type_requested,
            notes_for_driver=data.get('notes_for_driver'),
            estimated_fare=estimated_fare
        )
        db.session.add(new_ride)
        db.session.commit()

        ride_details = {
            'id': new_ride.id,
            'passenger_id': new_ride.passenger_id,
            'pickup_location': {
                'id': pickup_location.id,
                'latitude': pickup_location.latitude,
                'longitude': pickup_location.longitude,
                'address': pickup_location.address_line1
            },
            'dropoff_location': {
                'id': dropoff_location.id,
                'latitude': dropoff_location.latitude,
                'longitude': dropoff_location.longitude,
                'address': dropoff_location.address_line1
            },
            'status': new_ride.status,
            'requested_at': new_ride.requested_at.isoformat(),
            'vehicle_type_requested': new_ride.vehicle_type_requested,
            'notes_for_driver': new_ride.notes_for_driver
        }
        return jsonify({'message': 'Ride booked successfully', 'ride': ride_details}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error booking ride: {e}")
        return jsonify({'message': 'Failed to book ride due to an internal error'}), 500

@rides_bp.route('/history', methods=['GET'])
@token_required
def ride_history(current_user):
    try:
        # Fetch rides for the current user, ordered by most recent
        user_rides = Ride.query.filter_by(passenger_id=current_user.id)\
                               .order_by(Ride.requested_at.desc()).all()

        if not user_rides:
            return jsonify({'message': 'No ride history found for this user.', 'rides': []}), 200

        rides_data = []
        for ride in user_rides:
            pickup_loc = Location.query.get(ride.pickup_location_id)
            dropoff_loc = Location.query.get(ride.dropoff_location_id)
            
            ride_info = {
                'id': ride.id,
                'status': ride.status,
                'requested_at': ride.requested_at.isoformat() if ride.requested_at else None,
                'accepted_at': ride.accepted_at.isoformat() if ride.accepted_at else None,
                'started_at': ride.started_at.isoformat() if ride.started_at else None,
                'completed_at': ride.completed_at.isoformat() if ride.completed_at else None,
                'cancelled_at': ride.cancelled_at.isoformat() if ride.cancelled_at else None,
                'estimated_fare': ride.estimated_fare,
                'actual_fare': ride.actual_fare,
                'payment_status': ride.payment_status,
                'vehicle_type_requested': ride.vehicle_type_requested,
                'pickup_location': {
                    'latitude': pickup_loc.latitude if pickup_loc else None,
                    'longitude': pickup_loc.longitude if pickup_loc else None,
                    'address': pickup_loc.address_line1 if pickup_loc else None
                },
                'dropoff_location': {
                    'latitude': dropoff_loc.latitude if dropoff_loc else None,
                    'longitude': dropoff_loc.longitude if dropoff_loc else None,
                    'address': dropoff_loc.address_line1 if dropoff_loc else None
                }
                # Add driver info if ride.driver_id is not None and you want to include it
            }
            rides_data.append(ride_info)
        
        return jsonify({'rides': rides_data}), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching ride history: {e}")
        return jsonify({'message': 'Failed to fetch ride history due to an internal error'}), 500

@rides_bp.route('/<int:ride_id>/cancel', methods=['POST'])
@token_required
def cancel_ride(current_user, ride_id):
    try:
        ride = Ride.query.get(ride_id)

        if not ride:
            return jsonify({'message': 'Ride not found'}), 404

        # Ensure the current user is the passenger of the ride
        if ride.passenger_id != current_user.id:
            return jsonify({'message': 'You are not authorized to cancel this ride'}), 403 # Forbidden

        # Define cancellable statuses
        # Typically, a ride can be cancelled if it's REQUESTED or ACCEPTED
        # This logic can be adjusted based on business rules
        cancellable_statuses = ['REQUESTED', 'ACCEPTED']
        if ride.status not in cancellable_statuses:
            return jsonify({'message': f'Ride cannot be cancelled in its current status: {ride.status}'}), 400

        ride.status = 'CANCELLED_PASSENGER'
        ride.cancelled_at = datetime.datetime.utcnow()
        db.session.commit()

        return jsonify({'message': 'Ride cancelled successfully', 'ride_id': ride.id, 'new_status': ride.status}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error cancelling ride {ride_id}: {e}")
        return jsonify({'message': 'Failed to cancel ride due to an internal error'}), 500

@rides_bp.route('/<int:ride_id>/process-payment', methods=['POST'])
@token_required
def process_ride_payment(current_user, ride_id):
    try:
        ride = Ride.query.get(ride_id)

        if not ride:
            return jsonify({'message': 'Ride not found'}), 404

        # Ensure the current user is the passenger of the ride or an admin (for later)
        if ride.passenger_id != current_user.id:
            # Add admin check here in the future if needed
            return jsonify({'message': 'You are not authorized to process payment for this ride'}), 403

        # Check if ride is in a state where payment is expected (e.g., COMPLETED)
        if ride.status != 'COMPLETED': # Or other statuses like 'PENDING_PAYMENT'
            return jsonify({'message': f'Ride cannot be paid for in its current status: {ride.status}'}), 400
        
        if ride.payment_status == 'PAID':
            return jsonify({'message': 'This ride has already been paid for.'}), 400

        # Dummy payment processing logic
        data = request.get_json() or {}
        payment_method = data.get('payment_method', 'DUMMY_CARD') # e.g., 'CARD', 'UPI', 'WALLET'
        transaction_id = f"DUMMY_TXN_{datetime.datetime.utcnow().timestamp()}_{ride.id}"

        ride.payment_status = 'PAID'
        ride.payment_method = payment_method
        ride.payment_transaction_id = transaction_id
        ride.paid_at = datetime.datetime.utcnow()
        # ride.actual_fare could be confirmed here if it differs from estimated
        # For now, assume estimated_fare is the actual_fare upon completion
        if ride.actual_fare is None and ride.estimated_fare is not None:
            ride.actual_fare = ride.estimated_fare
            
        db.session.commit()

        return jsonify({
            'message': 'Payment processed successfully (dummy).',
            'ride_id': ride.id,
            'payment_status': ride.payment_status,
            'transaction_id': ride.payment_transaction_id,
            'paid_at': ride.paid_at.isoformat()
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing payment for ride {ride_id}: {e}")
        return jsonify({'message': 'Failed to process payment due to an internal error'}), 500

# Other ride-related routes will be added here
