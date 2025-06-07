from .. import db
import datetime
from datetime import timezone # Import timezone

class Ride(db.Model):
    __tablename__ = 'rides'

    id = db.Column(db.Integer, primary_key=True)
    passenger_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True) # Nullable until a driver accepts
    
    pickup_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    dropoff_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)

    # Consider using specific backrefs if User has separate 'rides_as_passenger' and 'rides_as_driver' relationships
    passenger = db.relationship('User', foreign_keys=[passenger_id], backref=db.backref('rides_as_passenger_explicit', lazy='dynamic'))
    driver = db.relationship('User', foreign_keys=[driver_id], backref=db.backref('rides_as_driver_explicit', lazy='dynamic'))

    pickup_location = db.relationship('Location', foreign_keys=[pickup_location_id], backref=db.backref('rides_from_here', lazy='dynamic'))
    dropoff_location = db.relationship('Location', foreign_keys=[dropoff_location_id], backref=db.backref('rides_to_here', lazy='dynamic'))

    status_choices = [
        ('REQUESTED', 'Requested'),
        ('ACCEPTED', 'Accepted'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED_PASSENGER', 'Cancelled by Passenger'),
        ('CANCELLED_DRIVER', 'Cancelled by Driver'),
        ('CANCELLED_ADMIN', 'Cancelled by Admin'), # New status
        ('NO_DRIVERS_FOUND', 'No Drivers Found')
    ]
    status = db.Column(db.String(50), default='REQUESTED', nullable=False, index=True) # e.g., REQUESTED, ACCEPTED, IN_PROGRESS, COMPLETED, CANCELLED

    requested_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    accepted_at = db.Column(db.DateTime, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    cancelled_at = db.Column(db.DateTime, nullable=True)

    estimated_fare = db.Column(db.Float, nullable=True)
    actual_fare = db.Column(db.Float, nullable=True)
    
    # Payment details (can be expanded)
    payment_status_choices = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed')
    ]
    payment_status = db.Column(db.String(50), default='PENDING', nullable=True)
    payment_intent_id = db.Column(db.String(255), nullable=True) # For Stripe or other payment gateways

    # Additional details
    vehicle_type_requested = db.Column(db.String(50), nullable=True) # e.g., SEDAN, SUV
    notes_for_driver = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Ride {self.id} from {self.pickup_location_id} to {self.dropoff_location_id} by User {self.passenger_id}>'
