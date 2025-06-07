from .. import db
import datetime
from datetime import timezone # Import timezone

class DriverProfile(db.Model):
    __tablename__ = 'driver_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)
    license_number = db.Column(db.String(50), unique=True, nullable=False)
    license_expiry_date = db.Column(db.Date, nullable=True)
    # Add other relevant fields like license_front_img_url, license_back_img_url, etc.
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    verification_notes = db.Column(db.Text, nullable=True)
    availability_status_choices = [
        ('AVAILABLE', 'Available'),
        ('BUSY', 'Busy'), # On a ride
        ('OFFLINE', 'Offline')
    ]
    availability_status = db.Column(db.String(20), default='OFFLINE', nullable=False, index=True)
    current_latitude = db.Column(db.Float, nullable=True) # Optional: if driver's location is tracked independently of vehicle
    current_longitude = db.Column(db.Float, nullable=True)
    last_location_update = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(timezone.utc), onupdate=lambda: datetime.datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('driver_profile', uselist=False, lazy='joined'))

    def __repr__(self):
        return f'<DriverProfile for User {self.user_id} - License: {self.license_number}>'
