from .. import db
import datetime
from datetime import timezone # Import timezone

class Vehicle(db.Model):
    __tablename__ = 'vehicles'

    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    # Or link to DriverProfile.id if preferred: driver_profile_id = db.Column(db.Integer, db.ForeignKey('driver_profiles.id'), nullable=False, index=True)
    
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    color = db.Column(db.String(30), nullable=True)
    license_plate = db.Column(db.String(20), unique=True, nullable=False, index=True)
    vehicle_type_choices = [
        ('SEDAN', 'Sedan'),
        ('SUV', 'SUV'),
        ('HATCHBACK', 'Hatchback'),
        ('MINIVAN', 'Minivan'),
        ('MOTORCYCLE', 'Motorcycle') # Example
    ]
    vehicle_type = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False) # Driver can mark a vehicle as inactive
    # Add other fields like registration_certificate_url, insurance_url, etc.

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.datetime.now(timezone.utc), onupdate=lambda: datetime.datetime.now(timezone.utc))

    driver = db.relationship('User', backref=db.backref('vehicles', lazy='dynamic'))
    # If linked to DriverProfile: 
    # driver_profile = db.relationship('DriverProfile', backref=db.backref('vehicles', lazy='dynamic'))

    def __repr__(self):
        return f'<Vehicle {self.id}: {self.make} {self.model} ({self.license_plate})>'
