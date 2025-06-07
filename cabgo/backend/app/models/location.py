from .. import db
import datetime

class Location(db.Model):
    __tablename__ = 'locations'

    id = db.Column(db.Integer, primary_key=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    address_line1 = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    postal_code = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Rides where this location is a pickup point
    # rides_from = db.relationship('Ride', foreign_keys='Ride.pickup_location_id', backref='pickup_loc', lazy=True)
    # Rides where this location is a dropoff point
    # rides_to = db.relationship('Ride', foreign_keys='Ride.dropoff_location_id', backref='dropoff_loc', lazy=True)

    def __repr__(self):
        return f'<Location {self.id}: ({self.latitude}, {self.longitude})>'
