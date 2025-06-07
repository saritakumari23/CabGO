from flask import Blueprint, request, jsonify, current_app
from .models import User, DriverProfile, Vehicle
from . import db
from .decorators import token_required
import datetime

vehicles_bp = Blueprint('vehicles', __name__)

@vehicles_bp.route('/add', methods=['POST'])
@token_required
def add_vehicle(current_user):
    # Ensure the user is a driver
    if not current_user.is_driver:
        return jsonify({'message': 'Only registered drivers can add vehicles.'}), 403
    
    # Optionally, check if the driver's profile is verified before allowing vehicle addition
    driver_profile = DriverProfile.query.filter_by(user_id=current_user.id).first()
    if not driver_profile or not driver_profile.is_verified:
        return jsonify({'message': 'Driver profile not found or not verified. Cannot add vehicle.'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    required_fields = ['make', 'model', 'license_plate', 'vehicle_type']
    for field in required_fields:
        if field not in data or not data[field]:
            return jsonify({'message': f'{field.replace("_", " ").capitalize()} is required'}), 400

    make = data.get('make')
    model = data.get('model')
    year = data.get('year') # Optional
    color = data.get('color') # Optional
    license_plate = data.get('license_plate')
    vehicle_type = data.get('vehicle_type')

    # Validate vehicle_type against choices in the model
    valid_vehicle_types = [choice[0] for choice in Vehicle.vehicle_type_choices]
    if vehicle_type not in valid_vehicle_types:
        return jsonify({'message': f'Invalid vehicle type. Must be one of: {valid_vehicle_types}'}), 400

    # Check if license plate is already registered
    if Vehicle.query.filter_by(license_plate=license_plate).first():
        return jsonify({'message': 'This license plate is already registered.'}), 409 # Conflict

    try:
        new_vehicle = Vehicle(
            driver_id=current_user.id,
            make=make,
            model=model,
            year=year,
            color=color,
            license_plate=license_plate,
            vehicle_type=vehicle_type,
            is_active=True # Default to active when added
        )
        db.session.add(new_vehicle)
        db.session.commit()

        vehicle_data = {
            'id': new_vehicle.id,
            'driver_id': new_vehicle.driver_id,
            'make': new_vehicle.make,
            'model': new_vehicle.model,
            'year': new_vehicle.year,
            'color': new_vehicle.color,
            'license_plate': new_vehicle.license_plate,
            'vehicle_type': new_vehicle.vehicle_type,
            'is_active': new_vehicle.is_active
        }
        return jsonify({'message': 'Vehicle added successfully.', 'vehicle': vehicle_data}), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding vehicle for driver {current_user.id}: {e}")
        return jsonify({'message': 'Failed to add vehicle due to an internal error'}), 500


@vehicles_bp.route('', methods=['GET']) # Changed to /api/vehicles
@token_required
def list_driver_vehicles(current_user):
    """Lists all vehicles registered by the authenticated driver."""
    if not current_user.is_driver:
        return jsonify({'message': 'Only drivers can view their vehicles.'}), 403

    # Optionally, check if the driver's profile exists, though is_driver should suffice
    # driver_profile = DriverProfile.query.filter_by(user_id=current_user.id).first()
    # if not driver_profile:
    #     return jsonify({'message': 'Driver profile not found.'}), 404

    vehicles = Vehicle.query.filter_by(driver_id=current_user.id).all()

    if not vehicles:
        return jsonify({'message': 'No vehicles found for this driver.', 'vehicles': []}), 200

    output = []
    for vehicle in vehicles:
        vehicle_data = {
            'id': vehicle.id,
            'make': vehicle.make,
            'model': vehicle.model,
            'year': vehicle.year,
            'color': vehicle.color,
            'license_plate': vehicle.license_plate,
            'vehicle_type': vehicle.vehicle_type,
            'is_active': vehicle.is_active,
            'created_at': vehicle.created_at.isoformat() if vehicle.created_at else None,
            'updated_at': vehicle.updated_at.isoformat() if vehicle.updated_at else None
        }
        output.append(vehicle_data)
    
    return jsonify({'vehicles': output}), 200

# Other vehicle-related routes (list, update, delete) can be added here
