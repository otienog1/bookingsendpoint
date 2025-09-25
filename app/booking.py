from . import db
from .models import TimestampMixin
from flask import current_app



class Booking(db.Model, TimestampMixin):
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date_from = db.Column(db.DateTime, nullable=False)
    date_to = db.Column(db.DateTime, nullable=False)
    country = db.Column(db.String(100), nullable=False)
    pax = db.Column(db.Integer, nullable=True)
    ladies = db.Column(db.Integer, nullable=True)
    men = db.Column(db.Integer, nullable=True)
    children = db.Column(db.Integer, nullable=True)
    teens = db.Column(db.Integer, nullable=True)

    # Replace string field with a foreign key reference to Agent model
    agent_id = db.Column(db.Integer, db.ForeignKey('agents.id'), nullable=True)

    # This will be removed later
    agent = db.Column(db.String(100), nullable=True)

    # Keep this field as legacy reference for backward compatibility or rename to something else if needed
    consultant = db.Column(db.String(100), nullable=True)

    # Foreign key reference to the user who created the booking
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Notes field for additional information
    notes = db.Column(db.Text, nullable=True)

    # Define relationship to User model
    user = db.relationship('User', backref=db.backref('bookings', lazy=True))

    # Define relationship to Agent model
    agent_relation = db.relationship('Agent', backref=db.backref('bookings', lazy=True), foreign_keys=[agent_id])

    @classmethod
    def get_all(cls):
        return cls.query.all()

    def to_dict(self):
        try:
            # Get agent information safely
            agent_name = None
            agent_country = None

            if self.agent_relation:
                agent_name = self.agent_relation.name
                agent_country = self.agent_relation.country

            # Get user information safely
            created_by = None
            if self.user:
                created_by = self.user.username

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
                "agent_id": self.agent_id,
                "agent_name": agent_name,
                "agent_country": agent_country,
                "consultant": self.consultant,
                "user_id": self.user_id,
                "created_by": created_by,
                "notes": self.notes
            }
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Error converting booking {self.id} to dict: {str(e)}")
            # Return a minimal dictionary with just the ID to avoid breaking the response
            return {"id": self.id, "error": "Error converting booking data"}