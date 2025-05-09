from datetime import datetime, timezone
from . import db
from .models import TimestampMixin


class Agent(db.Model, TimestampMixin):
    __tablename__ = 'agents'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    country = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    # Add foreign key reference to the user who created/manages the agent
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Define relationship to User model
    user = db.relationship('User', backref=db.backref('agents', lazy=True))

    # Define relationship to Booking model (will be set up in the Booking model)
    # bookings = db.relationship('Booking', backref='agent_details', lazy=True)

    @classmethod
    def get_all(cls):
        return cls.query.all()

    @classmethod
    def get_active(cls):
        return cls.query.filter_by(is_active=True).all()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "company": self.company,
            "email": self.email,
            "phone": self.phone,
            "country": self.country,
            "address": self.address,
            "notes": self.notes,
            "is_active": self.is_active,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }