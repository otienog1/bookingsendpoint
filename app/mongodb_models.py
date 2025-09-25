from datetime import datetime, timezone
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from . import mongo


class BaseModel:
    """Base class for MongoDB models"""
    
    @classmethod
    def get_collection(cls):
        """Get the MongoDB collection for this model"""
        return mongo.db[cls.__collection_name__]
    
    @classmethod
    def find_by_id(cls, id):
        """Find a document by ID"""
        if isinstance(id, str):
            id = ObjectId(id)
        return cls.get_collection().find_one({"_id": id})
    
    @classmethod
    def find_one(cls, query=None):
        """Find one document by query"""
        if query is None:
            query = {}
        return cls.get_collection().find_one(query)
    
    @classmethod
    def find_many(cls, query=None):
        """Find multiple documents by query"""
        if query is None:
            query = {}
        return list(cls.get_collection().find(query))
    
    @classmethod
    def insert_one(cls, document):
        """Insert one document"""
        document['created_at'] = datetime.now(timezone.utc)
        document['updated_at'] = datetime.now(timezone.utc)
        result = cls.get_collection().insert_one(document)
        return result.inserted_id
    
    @classmethod
    def update_one(cls, query, update):
        """Update one document"""
        update['$set'] = update.get('$set', {})
        update['$set']['updated_at'] = datetime.now(timezone.utc)
        return cls.get_collection().update_one(query, update)
    
    @classmethod
    def delete_one(cls, query):
        """Delete one document"""
        return cls.get_collection().delete_one(query)


class User(BaseModel):
    __collection_name__ = 'users'
    
    @classmethod
    def get_all(cls):
        """Get all users"""
        return cls.find_many()
    
    @classmethod
    def find_by_username(cls, username):
        """Find user by username"""
        return cls.find_one({"username": username})
    
    @classmethod
    def find_by_email(cls, email):
        """Find user by email"""
        return cls.find_one({"email": email})
    
    @classmethod
    def create_user(cls, username, email, password, first_name=None, last_name=None, role='user'):
        """Create a new user"""
        user_data = {
            "username": username,
            "email": email,
            "password_hash": generate_password_hash(password),
            "first_name": first_name,
            "last_name": last_name,
            "role": role,
            "is_active": True
        }
        user_id = cls.insert_one(user_data)
        return cls.find_by_id(user_id)
    
    @classmethod
    def check_password(cls, user_doc, password):
        """Check if password matches"""
        return check_password_hash(user_doc['password_hash'], password)
    
    @classmethod
    def update_password(cls, user_id, new_password):
        """Update user password"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        password_hash = generate_password_hash(new_password)
        return cls.update_one(
            {"_id": user_id},
            {"$set": {"password_hash": password_hash}}
        )
    
    @staticmethod
    def to_dict(user_doc):
        """Convert user document to dictionary"""
        if not user_doc:
            return None
        return {
            "id": str(user_doc["_id"]),
            "username": user_doc["username"],
            "email": user_doc["email"],
            "first_name": user_doc.get("first_name"),
            "last_name": user_doc.get("last_name"),
            "role": user_doc["role"],
            "is_active": user_doc["is_active"],
            "created_at": user_doc["created_at"],
            "updated_at": user_doc["updated_at"]
        }


class Agent(BaseModel):
    __collection_name__ = 'agents'
    
    @classmethod
    def get_all(cls):
        """Get all agents"""
        return cls.find_many()
    
    @classmethod
    def get_active(cls):
        """Get only active agents"""
        return cls.find_many({"is_active": True})
    
    @classmethod
    def find_by_email(cls, email):
        """Find agent by email"""
        return cls.find_one({"email": email})
    
    @classmethod
    def find_by_name(cls, name):
        """Find agent by name"""
        return cls.find_one({"name": name})
    
    @classmethod
    def create_agent(cls, name, email, country, user_id, company=None, phone=None, 
                    address=None, notes=None, is_active=True):
        """Create a new agent"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
            
        agent_data = {
            "name": name,
            "company": company,
            "email": email,
            "phone": phone,
            "country": country,
            "address": address,
            "notes": notes,
            "is_active": is_active,
            "user_id": user_id
        }
        agent_id = cls.insert_one(agent_data)
        return cls.find_by_id(agent_id)
    
    @staticmethod
    def to_dict(agent_doc):
        """Convert agent document to dictionary"""
        if not agent_doc:
            return None
        try:
            return {
                "id": str(agent_doc["_id"]),
                "name": agent_doc["name"],
                "company": agent_doc.get("company"),
                "email": agent_doc["email"],
                "phone": agent_doc.get("phone"),
                "country": agent_doc["country"],
                "address": agent_doc.get("address"),
                "notes": agent_doc.get("notes"),
                "is_active": agent_doc["is_active"],
                "user_id": str(agent_doc["user_id"]),
                "created_at": agent_doc["created_at"],
                "updated_at": agent_doc["updated_at"]
            }
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Error converting agent to dict: {str(e)}")
            return {"id": str(agent_doc["_id"]), "error": "Error converting agent data"}


class Booking(BaseModel):
    __collection_name__ = 'bookings'
    
    @classmethod
    def get_all(cls):
        """Get all bookings"""
        return cls.find_many()
    
    @classmethod
    def find_by_user(cls, user_id):
        """Find bookings by user"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        return cls.find_many({"user_id": user_id})
    
    @classmethod
    def find_by_agent(cls, agent_id):
        """Find bookings by agent"""
        if isinstance(agent_id, str):
            agent_id = ObjectId(agent_id)
        return cls.find_many({"agent_id": agent_id})
    
    @classmethod
    def create_booking(cls, name, date_from, date_to, country, user_id, agent_id,
                      pax=0, ladies=0, men=0, children=0, teens=0, consultant=None, notes=None):
        """Create a new booking"""
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        if isinstance(agent_id, str):
            agent_id = ObjectId(agent_id)

        booking_data = {
            "name": name,
            "date_from": date_from,
            "date_to": date_to,
            "country": country,
            "pax": pax,
            "ladies": ladies,
            "men": men,
            "children": children,
            "teens": teens,
            "agent_id": agent_id,
            "consultant": consultant,
            "user_id": user_id,
            "notes": notes,
            "is_deleted": False,
            "deleted_at": None
        }
        booking_id = cls.insert_one(booking_data)
        return cls.find_by_id(booking_id)

    @classmethod
    def get_active(cls):
        """Get only active (non-deleted) bookings"""
        return cls.find_many({"$or": [{"is_deleted": {"$exists": False}}, {"is_deleted": False}]})

    @classmethod
    def get_trashed(cls):
        """Get only trashed bookings"""
        return cls.find_many({"is_deleted": True})

    @classmethod
    def move_to_trash(cls, booking_id, user_id):
        """Move a booking to trash (soft delete)"""
        if isinstance(booking_id, str):
            booking_id = ObjectId(booking_id)
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)

        return cls.update_one(
            {"_id": booking_id},
            {"$set": {
                "is_deleted": True,
                "deleted_at": datetime.now(timezone.utc),
                "deleted_by": user_id
            }}
        )

    @classmethod
    def restore_from_trash(cls, booking_id):
        """Restore a booking from trash"""
        if isinstance(booking_id, str):
            booking_id = ObjectId(booking_id)

        return cls.update_one(
            {"_id": booking_id},
            {"$set": {
                "is_deleted": False,
                "deleted_at": None
            }, "$unset": {
                "deleted_by": ""
            }}
        )

    @classmethod
    def empty_trash(cls):
        """Permanently delete all trashed bookings"""
        return cls.get_collection().delete_many({"is_deleted": True})
    
    @staticmethod
    def to_dict(booking_doc, agent_doc=None, user_doc=None):
        """Convert booking document to dictionary"""
        if not booking_doc:
            return None
        try:
            result = {
                "id": str(booking_doc["_id"]),
                "name": booking_doc["name"],
                "date_from": booking_doc["date_from"],
                "date_to": booking_doc["date_to"],
                "country": booking_doc["country"],
                "pax": booking_doc.get("pax", 0),
                "ladies": booking_doc.get("ladies", 0),
                "men": booking_doc.get("men", 0),
                "children": booking_doc.get("children", 0),
                "teens": booking_doc.get("teens", 0),
                "agent_id": str(booking_doc["agent_id"]),
                "consultant": booking_doc.get("consultant"),
                "user_id": str(booking_doc["user_id"]),
                "notes": booking_doc.get("notes"),
                "is_deleted": booking_doc.get("is_deleted", False),
                "deleted_at": booking_doc.get("deleted_at"),
                "created_at": booking_doc["created_at"],
                "updated_at": booking_doc["updated_at"]
            }
            
            # Add agent information if provided
            if agent_doc:
                result["agent_name"] = agent_doc["name"]
                result["agent_country"] = agent_doc["country"]
            else:
                result["agent_name"] = None
                result["agent_country"] = None
            
            # Add user information if provided
            if user_doc:
                result["created_by"] = user_doc["username"]
            else:
                result["created_by"] = None
                
            return result
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Error converting booking to dict: {str(e)}")
            return {"id": str(booking_doc["_id"]), "error": "Error converting booking data"}