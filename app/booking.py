from datetime import datetime, timezone
from enum import unique
from . import db

from .models import TimestampMixin


class Booking(db.Model, TimestampMixin):
    # __table
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    date_from = db.Column(db.DateTime, nullable=False)
    date_to = db.Column(db.DateTime, nullable=False)
    country = db.Column(db.String(100), nullable=False)
    pax = db.Column(db.Integer, nullable=True)
    ladies = db.Column(db.Integer, nullable=True)
    men = db.Column(db.Integer, nullable=True)
    children = db.Column(db.Integer, nullable=True)
    teens = db.Column(db.Integer, nullable=True)
    agent = db.Column(db.String(100), nullable=False)
    consultant = db.Column(db.String(100), nullable=False)

    # Add foreign key reference to the user who created the booking
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Define relationship to User model
    user = db.relationship('User', backref=db.backref('booking', lazy=True))

    @classmethod
    def get_all(cls):
        return cls.query.all()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "date_from": self.date_from,
            "date_to": self.date_to,
            "country": self.country,
            "pax": self.pax,
            "ladies": self.ladies,
            "men": self.men,
            "children": self.children,
            "teens": self.teens,
            "agent": self.agent,
            "consultant": self.consultant,
            "user_id": self.user_id,
            "created_by": self.user.username if self.user else None
        }