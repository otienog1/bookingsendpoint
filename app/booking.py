from datetime import datetime, timezone
from enum import unique
from . import db


class TimestampMixin(object):
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.now(timezone.utc),
        onupdate=datetime.now(timezone.utc),
    )


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
        }
