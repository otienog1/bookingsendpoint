from flask import Blueprint, jsonify, request, current_app
from .mongodb_models import Booking, Agent, User
from . import mongo
from bson import ObjectId
from .authbp import token_required
import csv
from datetime import datetime
import traceback

bookingsbp = Blueprint("bookingsbp", __name__)


@bookingsbp.route("/booking/fetch", methods=("GET",))
@token_required
def fetch_bookings(current_user):
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

        # Non-admin users can only see their own bookings
        if current_user['role'] != 'admin':
            mongo_query['user_id'] = current_user['_id']

        # Log the MongoDB query for debugging
        current_app.logger.debug(f"MongoDB Query: {mongo_query}")

        bookings = Booking.find_many(mongo_query)
        current_app.logger.info(f"Successfully fetched {len(bookings)} bookings")

        # Get agent and user information for each booking
        bookings_data = []
        for booking in bookings:
            try:
                # Get agent info
                agent_doc = None
                if booking.get('agent_id'):
                    agent_doc = Agent.find_by_id(booking['agent_id'])

                # Get user info
                user_doc = None
                if booking.get('user_id'):
                    user_doc = User.find_by_id(booking['user_id'])

                booking_dict = Booking.to_dict(booking, agent_doc, user_doc)
                bookings_data.append(booking_dict)
            except Exception as e:
                current_app.logger.error(f"Error converting booking {booking['_id']} to dict: {str(e)}")
                current_app.logger.error(traceback.format_exc())
                # Continue with other bookings even if one fails

        return jsonify({"bookings": bookings_data})

    except Exception as e:
        error_msg = f"Error fetching bookings: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "An error occurred while fetching bookings data"}), 500


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
            consultant=data.get("consultant")
        )

        current_app.logger.info(f"Booking created successfully with ID {booking['_id']}")

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
                    consultant=row.get("consultant")
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