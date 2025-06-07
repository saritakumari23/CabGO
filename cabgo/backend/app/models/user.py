from .. import db # Import the db instance from the app package (__init__.py)
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
from datetime import timezone # Import timezone

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=True, index=True)
    is_driver = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(timezone.utc), onupdate=lambda: datetime.datetime.now(timezone.utc))

    # Relationships defined in Ride model using backref or backref name
    # rides_as_passenger_explicit is created by backref in Ride.passenger
    # rides_as_driver_explicit is created by backref in Ride.driver

    # If you prefer to define them here explicitly for clarity or different loading:
    # rides_as_passenger = db.relationship('Ride', foreign_keys='Ride.passenger_id', backref='passenger_user', lazy='dynamic')
    # rides_as_driver = db.relationship('Ride', foreign_keys='Ride.driver_id', backref='driver_user', lazy='dynamic')

    # driver_profile is created by backref in DriverProfile.user

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'
