from flask import Blueprint, jsonify, request, current_app
from .mongodb_models import Booking, Agent, User
from . import mongo
from bson import ObjectId
from .authbp import token_required
import csv
from datetime import datetime
import traceback
import jwt
import os
import secrets
import time

bookingsbp = Blueprint("bookingsbp", __name__)


def generate_share_token_for_booking(booking_id, user_id, categories=['Voucher', 'Air Ticket'], expires_in_seconds=604800):
    """Generate a share token for a newly created booking."""
    try:
        # Generate a short random token ID
        token_id = secrets.token_urlsafe(16)
        expires_at_timestamp = int(time.time()) + expires_in_seconds
        expires_at_datetime = datetime.fromtimestamp(expires_at_timestamp)

        # Create share URL
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')
        share_url = f"{frontend_url}/share/{token_id}"

        # Store share token in database
        share_record = {
            "booking_id": ObjectId(booking_id),
            "token": token_id,
            "categories": categories,
            "expires_at": expires_at_datetime,
            "created_at": datetime.utcnow(),
            "created_by": ObjectId(user_id),
            "used_count": 0
        }

        mongo.db.share_tokens.insert_one(share_record)

        current_app.logger.info(f"Auto-generated share token for booking {booking_id}: {token_id}")

        return {
            "token": token_id,
            "shareUrl": share_url,
            "expiresAt": expires_at_datetime.isoformat(),
            "categories": categories
        }
    except Exception as e:
        current_app.logger.error(f"Error auto-generating share token for booking {booking_id}: {str(e)}")
        return None


@bookingsbp.route("/booking/fetch", methods=("GET",))
@token_required
def fetch_bookings(current_user):
    """Original booking fetch endpoint."""
    return _fetch_bookings_logic(current_user)


def _fetch_bookings_logic(current_user):
    """Shared logic for fetching bookings."""
    try:
        current_app.logger.info(f"User {current_user['username']} requesting bookings data")

        # Filter options
        agent_id = request.args.get('agent_id')
        country = request.args.get('country')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

        current_app.logger.debug(
            f"Filters - agent_id: {agent_id}, country: {country}, date_from: {date_from}, date_to: {date_to}")

        # Build MongoDB query
        mongo_query = {}

        # Exclude deleted/trashed bookings by default
        mongo_query['$or'] = [
            {"is_deleted": {"$exists": False}},
            {"is_deleted": False}
        ]

        # Apply filters if provided
        if agent_id:
            mongo_query['agent_id'] = ObjectId(agent_id)
        if country:
            mongo_query['country'] = country
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%m/%d/%Y")
                mongo_query['date_from'] = {"$gte": from_date}
            except ValueError as e:
                current_app.logger.warning(f"Invalid date_from format: {date_from}. Error: {str(e)}")
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%m/%d/%Y")
                if 'date_to' not in mongo_query:
                    mongo_query['date_to'] = {}
                mongo_query['date_to']["$lte"] = to_date
            except ValueError as e:
                current_app.logger.warning(f"Invalid date_to format: {date_to}. Error: {str(e)}")

        # Allow all authenticated users to see all bookings for dashboard stats
        current_app.logger.info(f"Current user role: {current_user.get('role', 'unknown')}")
        current_app.logger.info(f"User: {current_user.get('username', 'unknown')}")

        # IMPORTANT: Explicitly ensure NO user filtering is applied
        if 'user_id' in mongo_query:
            del mongo_query['user_id']
            current_app.logger.info("Removed user_id filter to show all bookings")

        current_app.logger.info("No user filtering applied - showing all bookings")

        # Log the MongoDB query for debugging
        current_app.logger.info(f"FINAL MongoDB Query: {mongo_query}")

        # Use aggregation pipeline to join with agents and users collections
        pipeline = [
            {"$match": mongo_query},
            {
                "$lookup": {
                    "from": "agents",
                    "localField": "agent_id",
                    "foreignField": "_id",
                    "as": "agent"
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {
                "$addFields": {
                    "agent": {"$arrayElemAt": ["$agent", 0]},
                    "user": {"$arrayElemAt": ["$user", 0]}
                }
            }
        ]

        bookings = list(mongo.db.bookings.aggregate(pipeline))
        current_app.logger.info(f"Successfully fetched {len(bookings)} bookings with joins")

        # Convert to dict format
        bookings_data = []
        for booking in bookings:
            try:
                booking_dict = Booking.to_dict(booking, booking.get('agent'), booking.get('user'))
                bookings_data.append(booking_dict)
            except Exception as e:
                current_app.logger.error(f"Error converting booking {booking['_id']} to dict: {str(e)}")

        return jsonify({"bookings": bookings_data})

    except Exception as e:
        error_msg = f"Error fetching bookings: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "An error occurred while fetching bookings data"}), 500


@bookingsbp.route("/api/booking/fetch", methods=("GET",))
@token_required
def api_fetch_bookings(current_user):
    """API endpoint alias for booking fetch."""
    return _fetch_bookings_logic(current_user)


@bookingsbp.route("/booking/<booking_id>", methods=("GET", "OPTIONS"))
def get_booking(booking_id):
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'OK'})
        return response
    
    # For GET requests, apply token authentication
    token = None
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]

    if not token:
        return jsonify({'error': 'Token is missing!'}), 401

    try:
        # Decode token (simplified version of token_required logic)
        
        data = jwt.decode(token, current_app.config['SECRET_KEY'],
                          algorithms=[current_app.config['JWT_ALGORITHM']])
        current_user = User.find_by_id(data['user_id'])

        if not current_user:
            return jsonify({'error': 'User no longer exists!'}), 401

    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token has expired!'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token!'}), 401
    except Exception as e:
        return jsonify({'error': 'Authentication failed!'}), 401

    # Main booking retrieval logic
    try:
        current_app.logger.info(f"Fetching booking with ID: {booking_id} for user: {current_user['username']}")
        
        # Validate ObjectId format - must be 24 hex characters
        if not booking_id or len(booking_id) != 24:
            current_app.logger.error(f"Invalid booking ID format: {booking_id} (length: {len(booking_id) if booking_id else 0})")
            return jsonify({"error": "Invalid booking ID format"}), 400

        # Validate if it's a valid hex string for ObjectId
        try:
            ObjectId(booking_id)
        except Exception as e:
            current_app.logger.error(f"Invalid ObjectId format: {booking_id}, error: {str(e)}")
            return jsonify({"error": "Invalid booking ID format"}), 400
        
        booking = Booking.find_by_id(booking_id)
        current_app.logger.info(f"Database query result: {booking is not None}")
        
        if not booking:
            current_app.logger.warning(f"Booking not found: {booking_id}")
            return jsonify({"error": "Booking not found."}), 404
        
        current_app.logger.info(f"Converting booking to dict...")
        
        # Fetch related agent and user information
        agent_doc = None
        user_doc = None
        
        if booking.get('agent_id'):
            agent_doc = Agent.find_by_id(booking['agent_id'])
            
        if booking.get('user_id'):
            user_doc = User.find_by_id(booking['user_id'])
        
        booking_dict = Booking.to_dict(booking, agent_doc, user_doc)
        current_app.logger.info(f"Successfully converted booking: {booking_dict['id']}")
        
        return jsonify({"booking": booking_dict})
    
    except Exception as e:
        current_app.logger.error(f"Error fetching booking {booking_id}: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@bookingsbp.route("/api/booking/<booking_id>", methods=("GET", "OPTIONS"))
def api_get_booking(booking_id):
    """API endpoint alias for getting booking by ID."""
    return get_booking(booking_id)


@bookingsbp.route("/booking/create", methods=("POST",))
@token_required
def create_booking(current_user):
    data = request.get_json()
    current_app.logger.info(f"User {current_user['username']} attempting to create booking")
    current_app.logger.debug(f"Create booking data: {data}")

    try:
        # Use current_user._id if user_id is not provided in the request
        user_id = data.get("user_id", str(current_user['_id']))

        # Verify the agent exists
        agent_id = data["agent_id"]
        agent = Agent.find_by_id(agent_id)
        if not agent:
            current_app.logger.warning(f"Agent with ID {agent_id} not found")
            return jsonify({"error": "Agent not found."}), 404

        # Only admins can create bookings for other users
        if user_id != str(current_user['_id']) and current_user['role'] != 'admin':
            current_app.logger.warning(
                f"Unauthorized attempt to create booking for user {user_id} by {current_user['username']}")
            return jsonify({"error": "Unauthorized access!"}), 403

        booking = Booking.create_booking(
            name=data["name"],
            date_from=datetime.strptime(data["date_from"], "%m/%d/%Y"),
            date_to=datetime.strptime(data["date_to"], "%m/%d/%Y"),
            country=data["country"],
            user_id=user_id,
            agent_id=agent_id,
            pax=int(data["pax"]) if data["pax"] else 0,
            ladies=int(data["ladies"]) if data["ladies"] else 0,
            men=int(data["men"]) if data["men"] else 0,
            children=int(data["children"]) if data["children"] else 0,
            teens=int(data["teens"]) if data["teens"] else 0,
            consultant=data.get("consultant"),
            notes=data.get("notes")
        )

        current_app.logger.info(f"Booking created successfully with ID {booking['_id']}")

        # Auto-generate share link for the new booking
        share_info = generate_share_token_for_booking(
            booking_id=str(booking['_id']),
            user_id=str(current_user['_id']),
            categories=['Voucher', 'Air Ticket', 'Invoice', 'Other'],  # Include all categories
            expires_in_seconds=604800  # 7 days
        )

    except KeyError as e:
        error_msg = f"Missing required field: {str(e)}"
        current_app.logger.error(error_msg)
        return jsonify({"error": error_msg}), 400
    except ValueError as e:
        error_msg = f"Invalid data format: {str(e)}"
        current_app.logger.error(error_msg)
        return jsonify({"error": error_msg}), 400
    except Exception as e:
        error_msg = f"Error creating booking: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": error_msg}), 400

    # Get agent and user info for response
    agent_doc = Agent.find_by_id(booking['agent_id'])
    user_doc = User.find_by_id(booking['user_id'])
    return jsonify({"booking": Booking.to_dict(booking, agent_doc, user_doc)})


@bookingsbp.route("/booking/edit/<booking_id>", methods=("PUT",))
@token_required
def edit_booking(current_user, booking_id):
    data = request.get_json()
    current_app.logger.info(f"User {current_user['username']} attempting to edit booking {booking_id}")
    current_app.logger.debug(f"Edit booking data: {data}")

    try:
        # Validate ObjectId format - must be 24 hex characters
        if not booking_id or len(booking_id) != 24:
            current_app.logger.error(f"Invalid booking ID format for edit: {booking_id} (length: {len(booking_id) if booking_id else 0})")
            return jsonify({"error": "Invalid booking ID format"}), 400

        # Validate if it's a valid hex string for ObjectId
        try:
            ObjectId(booking_id)
        except Exception as e:
            current_app.logger.error(f"Invalid ObjectId format for edit: {booking_id}, error: {str(e)}")
            return jsonify({"error": "Invalid booking ID format"}), 400

        booking = Booking.find_by_id(booking_id)

        if not booking:
            current_app.logger.warning(f"Booking with ID {booking_id} not found")
            return jsonify({"error": "Booking not found."}), 404

        # Check if the user has permission to edit this booking
        if str(booking['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            current_app.logger.warning(f"Unauthorized attempt to edit booking {booking_id} by {current_user['username']}")
            return jsonify({"error": "Unauthorized access!"}), 403

        # Prepare update data
        update_data = {}

        # Verify the agent exists if agent_id is being changed
        if "agent_id" in data:
            agent_id = data["agent_id"]
            agent = Agent.find_by_id(agent_id)
            if not agent:
                current_app.logger.warning(f"Agent with ID {agent_id} not found during booking edit")
                return jsonify({"error": "Agent not found."}), 404
            update_data["agent_id"] = ObjectId(agent_id)

        if "name" in data:
            update_data["name"] = data["name"]
        if "date_from" in data:
            update_data["date_from"] = datetime.strptime(data["date_from"], "%m/%d/%Y")
        if "date_to" in data:
            update_data["date_to"] = datetime.strptime(data["date_to"], "%m/%d/%Y")
        if "country" in data:
            update_data["country"] = data["country"]
        if "pax" in data:
            update_data["pax"] = int(data["pax"])
        if "ladies" in data:
            update_data["ladies"] = int(data["ladies"])
        if "men" in data:
            update_data["men"] = int(data["men"])
        if "children" in data:
            update_data["children"] = int(data["children"])
        if "teens" in data:
            update_data["teens"] = int(data["teens"])
        if "consultant" in data:
            update_data["consultant"] = data["consultant"]
        if "notes" in data:
            update_data["notes"] = data["notes"]

        # Only admins can change the user_id
        if data.get("user_id") and current_user['role'] == 'admin':
            update_data["user_id"] = ObjectId(data["user_id"])

        if update_data:
            Booking.update_one(
                {"_id": ObjectId(booking_id)},
                {"$set": update_data}
            )

        current_app.logger.info(f"Booking {booking_id} updated successfully")

    except ValueError as e:
        error_msg = f"Invalid data format: {str(e)}"
        current_app.logger.error(error_msg)
        return jsonify({"error": error_msg}), 400
    except Exception as e:
        error_msg = f"Error updating booking: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": error_msg}), 400

    # Get updated booking with agent and user info
    updated_booking = Booking.find_by_id(booking_id)
    agent_doc = Agent.find_by_id(updated_booking['agent_id'])
    user_doc = User.find_by_id(updated_booking['user_id'])
    return jsonify({"booking": Booking.to_dict(updated_booking, agent_doc, user_doc)})


@bookingsbp.route("/booking/import", methods=("POST",))
@token_required
def import_bookings(current_user):
    current_app.logger.info(f"User {current_user['username']} attempting to import bookings")

    file = request.files.get("file")
    if not file:
        current_app.logger.warning("No file provided for import")
        return jsonify({"error": "No file provided."}), 400

    if not file.filename.endswith(".csv"):
        current_app.logger.warning(f"Invalid file format: {file.filename}")
        return jsonify({"error": "Invalid file format. Please upload a CSV file."}), 400

    try:
        content = file.stream.read().decode("utf-8").splitlines()
        current_app.logger.debug(f"Importing CSV with {len(content)} lines")

        csv_reader = csv.DictReader(content)
        imported_count = 0
        error_count = 0
        errors = []

        for row in csv_reader:
            try:
                # Find agent by name or agent_id
                agent_name = row.get("agent")
                agent_id = row.get("agent_id")

                agent = None
                if agent_name:
                    agent = Agent.find_by_name(agent_name)
                elif agent_id:
                    agent = Agent.find_by_id(agent_id)

                if not agent:
                    error_message = f"Agent not found for booking '{row.get('name')}'"
                    current_app.logger.warning(error_message)
                    errors.append(error_message)
                    error_count += 1
                    continue

                Booking.create_booking(
                    name=row["name"],
                    date_from=datetime.strptime(row["date_from"], "%m/%d/%Y"),
                    date_to=datetime.strptime(row["date_to"], "%m/%d/%Y"),
                    country=row["country"],
                    user_id=str(current_user['_id']),
                    agent_id=str(agent['_id']),
                    pax=int(row["pax"]) if row["pax"] else 0,
                    ladies=int(row["ladies"]) if row["ladies"] else 0,
                    men=int(row["men"]) if row["men"] else 0,
                    children=int(row["children"]) if row["children"] else 0,
                    teens=int(row["teens"]) if row["teens"] else 0,
                    consultant=row.get("consultant"),
                    notes=row.get("notes")
                )

                imported_count += 1

            except Exception as e:
                error_message = f"Error on row {csv_reader.line_num}: {str(e)}"
                current_app.logger.error(error_message)
                errors.append(error_message)
                error_count += 1

        current_app.logger.info(f"Successfully imported {imported_count} bookings with {error_count} errors")

        result = {
            "message": f"{imported_count} bookings imported successfully.",
            "imported": imported_count,
            "errors": error_count
        }

        if errors:
            result["error_details"] = errors

        return jsonify(result)

    except Exception as e:
        error_msg = f"Error importing bookings: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": error_msg}), 400


@bookingsbp.route("/booking/delete/<booking_id>", methods=("DELETE",))
@token_required
def delete_booking(current_user, booking_id):
    current_app.logger.info(f"User {current_user['username']} attempting to delete booking {booking_id}")

    try:
        # Validate ObjectId format - must be 24 hex characters
        if not booking_id or len(booking_id) != 24:
            current_app.logger.error(f"Invalid booking ID format for delete: {booking_id} (length: {len(booking_id) if booking_id else 0})")
            return jsonify({"error": "Invalid booking ID format"}), 400

        # Validate if it's a valid hex string for ObjectId
        try:
            ObjectId(booking_id)
        except Exception as e:
            current_app.logger.error(f"Invalid ObjectId format for delete: {booking_id}, error: {str(e)}")
            return jsonify({"error": "Invalid booking ID format"}), 400

        booking = Booking.find_by_id(booking_id)
        if not booking:
            current_app.logger.warning(f"Booking with ID {booking_id} not found")
            return jsonify({"error": "Booking not found."}), 404

        # Check if the user has permission to delete this booking
        if str(booking['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            current_app.logger.warning(
                f"Unauthorized attempt to delete booking {booking_id} by {current_user['username']}")
            return jsonify({"error": "Unauthorized access!"}), 403

        Booking.delete_one({"_id": ObjectId(booking_id)})
        current_app.logger.info(f"Booking {booking_id} deleted successfully")

    except Exception as e:
        error_msg = f"Error deleting booking: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": error_msg}), 400

    return jsonify({"message": "Booking deleted successfully."})


@bookingsbp.route("/booking/trash/<booking_id>", methods=("PUT",))
@token_required
def move_booking_to_trash(current_user, booking_id):
    """Move a booking to trash (soft delete)"""
    current_app.logger.info(f"User {current_user['username']} attempting to move booking {booking_id} to trash")

    try:
        # Validate ObjectId format - must be 24 hex characters
        if not booking_id or len(booking_id) != 24:
            current_app.logger.error(f"Invalid booking ID format for trash: {booking_id} (length: {len(booking_id) if booking_id else 0})")
            return jsonify({"error": "Invalid booking ID format"}), 400

        # Validate if it's a valid hex string for ObjectId
        try:
            ObjectId(booking_id)
        except Exception as e:
            current_app.logger.error(f"Invalid ObjectId format for trash: {booking_id}, error: {str(e)}")
            return jsonify({"error": "Invalid booking ID format"}), 400

        booking = Booking.find_by_id(booking_id)
        if not booking:
            current_app.logger.warning(f"Booking with ID {booking_id} not found")
            return jsonify({"error": "Booking not found."}), 404

        # Check if the user has permission to delete this booking
        if str(booking['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            current_app.logger.warning(
                f"Unauthorized attempt to trash booking {booking_id} by {current_user['username']}")
            return jsonify({"error": "Unauthorized access!"}), 403

        # Check if already deleted
        if booking.get('is_deleted', False):
            current_app.logger.warning(f"Booking {booking_id} is already in trash")
            return jsonify({"error": "Booking is already in trash."}), 400

        result = Booking.move_to_trash(booking_id, current_user['_id'])
        if result.modified_count > 0:
            current_app.logger.info(f"Booking {booking_id} moved to trash successfully")
        else:
            current_app.logger.warning(f"Failed to move booking {booking_id} to trash")
            return jsonify({"error": "Failed to move booking to trash."}), 500

    except Exception as e:
        error_msg = f"Error moving booking to trash: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": error_msg}), 500

    return jsonify({"message": "Booking moved to trash successfully."})


@bookingsbp.route("/booking/restore/<booking_id>", methods=("PUT",))
@token_required
def restore_booking(current_user, booking_id):
    """Restore a booking from trash"""
    current_app.logger.info(f"User {current_user['username']} attempting to restore booking {booking_id}")

    try:
        # Validate ObjectId format - must be 24 hex characters
        if not booking_id or len(booking_id) != 24:
            current_app.logger.error(f"Invalid booking ID format for restore: {booking_id} (length: {len(booking_id) if booking_id else 0})")
            return jsonify({"error": "Invalid booking ID format"}), 400

        # Validate if it's a valid hex string for ObjectId
        try:
            ObjectId(booking_id)
        except Exception as e:
            current_app.logger.error(f"Invalid ObjectId format for restore: {booking_id}, error: {str(e)}")
            return jsonify({"error": "Invalid booking ID format"}), 400

        booking = Booking.find_by_id(booking_id)
        if not booking:
            current_app.logger.warning(f"Booking with ID {booking_id} not found")
            return jsonify({"error": "Booking not found."}), 404

        # Check if the user has permission to restore this booking
        if str(booking['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            current_app.logger.warning(
                f"Unauthorized attempt to restore booking {booking_id} by {current_user['username']}")
            return jsonify({"error": "Unauthorized access!"}), 403

        # Check if it's actually deleted
        if not booking.get('is_deleted', False):
            current_app.logger.warning(f"Booking {booking_id} is not in trash")
            return jsonify({"error": "Booking is not in trash."}), 400

        result = Booking.restore_from_trash(booking_id)
        if result.modified_count > 0:
            current_app.logger.info(f"Booking {booking_id} restored successfully")
        else:
            current_app.logger.warning(f"Failed to restore booking {booking_id}")
            return jsonify({"error": "Failed to restore booking."}), 500

    except Exception as e:
        error_msg = f"Error restoring booking: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": error_msg}), 500

    return jsonify({"message": "Booking restored successfully."})


@bookingsbp.route("/booking/trash", methods=("GET",))
@token_required
def fetch_trashed_bookings(current_user):
    """Fetch all trashed bookings"""
    current_app.logger.info(f"User {current_user['username']} requesting trashed bookings")

    try:
        # Use aggregation pipeline to join with agents and users collections for trashed bookings
        pipeline = [
            {"$match": {"is_deleted": True}},
            {
                "$lookup": {
                    "from": "agents",
                    "localField": "agent_id",
                    "foreignField": "_id",
                    "as": "agent"
                }
            },
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user"
                }
            },
            {
                "$addFields": {
                    "agent": {"$arrayElemAt": ["$agent", 0]},
                    "user": {"$arrayElemAt": ["$user", 0]}
                }
            }
        ]

        bookings = list(mongo.db.bookings.aggregate(pipeline))
        current_app.logger.info(f"Successfully fetched {len(bookings)} trashed bookings")

        # Convert to dict format
        bookings_data = []
        for booking in bookings:
            try:
                booking_dict = Booking.to_dict(booking, booking.get('agent'), booking.get('user'))
                bookings_data.append(booking_dict)
            except Exception as e:
                current_app.logger.error(f"Error converting trashed booking {booking['_id']} to dict: {str(e)}")

        return jsonify({"bookings": bookings_data})

    except Exception as e:
        error_msg = f"Error fetching trashed bookings: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "An error occurred while fetching trashed bookings"}), 500


@bookingsbp.route("/booking/empty-trash", methods=("DELETE",))
@token_required
def empty_trash(current_user):
    """Permanently delete all trashed bookings"""
    current_app.logger.info(f"User {current_user['username']} attempting to empty trash")

    # Only admins can empty trash
    if current_user['role'] != 'admin':
        current_app.logger.warning(f"Unauthorized attempt to empty trash by {current_user['username']}")
        return jsonify({"error": "Unauthorized access! Only admins can empty trash."}), 403

    try:
        result = Booking.empty_trash()
        deleted_count = result.deleted_count
        current_app.logger.info(f"Successfully deleted {deleted_count} bookings from trash")

        return jsonify({
            "message": f"Trash emptied successfully. {deleted_count} bookings permanently deleted.",
            "deleted_count": deleted_count
        })

    except Exception as e:
        error_msg = f"Error emptying trash: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": error_msg}), 500