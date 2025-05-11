from flask import Blueprint, jsonify, request, current_app
from .booking import Booking
from .agent import Agent
from . import db
from .authbp import token_required
import csv
from datetime import datetime
import traceback

bookingsbp = Blueprint("bookingsbp", __name__)


@bookingsbp.route("/booking/fetch", methods=("GET",))
@token_required
def fetch_bookings(current_user):
    try:
        current_app.logger.info(f"User {current_user.username} requesting bookings data")

        # Filter options
        agent_id = request.args.get('agent_id')
        country = request.args.get('country')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')

        current_app.logger.debug(
            f"Filters - agent_id: {agent_id}, country: {country}, date_from: {date_from}, date_to: {date_to}")

        # Start with base query
        query = Booking.query

        # Apply filters if provided
        if agent_id:
            query = query.filter(Booking.agent_id == agent_id)
        if country:
            query = query.filter(Booking.country == country)
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%m/%d/%Y")
                query = query.filter(Booking.date_from >= from_date)
            except ValueError as e:
                current_app.logger.warning(f"Invalid date_from format: {date_from}. Error: {str(e)}")
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%m/%d/%Y")
                query = query.filter(Booking.date_to <= to_date)
            except ValueError as e:
                current_app.logger.warning(f"Invalid date_to format: {date_to}. Error: {str(e)}")

        # Non-admin users can only see their own bookings
        if current_user.role != 'admin':
            query = query.filter(Booking.user_id == current_user.id)

        # Log the SQL query for debugging
        current_app.logger.debug(f"SQL Query: {query}")

        bookings = query.all()
        current_app.logger.info(f"Successfully fetched {len(bookings)} bookings")

        # Check for agent relationships
        bookings_data = []
        for booking in bookings:
            try:
                booking_dict = booking.to_dict()
                bookings_data.append(booking_dict)
            except Exception as e:
                current_app.logger.error(f"Error converting booking {booking.id} to dict: {str(e)}")
                current_app.logger.error(traceback.format_exc())
                # Continue with other bookings even if one fails

        # Fix: Return the bookings_data list instead of the raw bookings objects
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
    current_app.logger.info(f"User {current_user.username} attempting to create booking")
    current_app.logger.debug(f"Create booking data: {data}")

    try:
        # Use current_user.id if user_id is not provided in the request
        user_id = data.get("user_id", current_user.id)

        # Verify the agent exists
        agent_id = data["agent_id"]
        agent = Agent.query.get(agent_id)
        if not agent:
            current_app.logger.warning(f"Agent with ID {agent_id} not found")
            return jsonify({"error": "Agent not found."}), 404

        # Only admins can create bookings for other users
        if user_id != current_user.id and current_user.role != 'admin':
            current_app.logger.warning(
                f"Unauthorized attempt to create booking for user {user_id} by {current_user.username}")
            return jsonify({"error": "Unauthorized access!"}), 403

        booking = Booking(
            name=data["name"],
            date_from=datetime.strptime(data["date_from"], "%m/%d/%Y"),
            date_to=datetime.strptime(data["date_to"], "%m/%d/%Y"),
            country=data["country"],
            pax=int(data["pax"]) if data["pax"] else 0,
            ladies=int(data["ladies"]) if data["ladies"] else 0,
            men=int(data["men"]) if data["men"] else 0,
            children=int(data["children"]) if data["children"] else 0,
            teens=int(data["teens"]) if data["teens"] else 0,
            agent_id=agent_id,
            consultant=data["consultant"],
            user_id=user_id
        )

        db.session.add(booking)
        db.session.commit()
        current_app.logger.info(f"Booking created successfully with ID {booking.id}")

    except KeyError as e:
        db.session.rollback()
        error_msg = f"Missing required field: {str(e)}"
        current_app.logger.error(error_msg)
        return jsonify({"error": error_msg}), 400
    except ValueError as e:
        db.session.rollback()
        error_msg = f"Invalid data format: {str(e)}"
        current_app.logger.error(error_msg)
        return jsonify({"error": error_msg}), 400
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error creating booking: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": error_msg}), 400

    return jsonify({"booking": booking.to_dict()})


@bookingsbp.route("/booking/edit/<int:booking_id>", methods=("PUT",))
@token_required
def edit_booking(current_user, booking_id):
    data = request.get_json()
    current_app.logger.info(f"User {current_user.username} attempting to edit booking {booking_id}")
    current_app.logger.debug(f"Edit booking data: {data}")

    try:
        booking = Booking.query.get(booking_id)

        if not booking:
            current_app.logger.warning(f"Booking with ID {booking_id} not found")
            return jsonify({"error": "Booking not found."}), 404

        # Check if the user has permission to edit this booking
        if booking.user_id != current_user.id and current_user.role != 'admin':
            current_app.logger.warning(f"Unauthorized attempt to edit booking {booking_id} by {current_user.username}")
            return jsonify({"error": "Unauthorized access!"}), 403

        # Verify the agent exists if agent_id is being changed
        if "agent_id" in data:
            agent_id = data["agent_id"]
            agent = Agent.query.get(agent_id)
            if not agent:
                current_app.logger.warning(f"Agent with ID {agent_id} not found during booking edit")
                return jsonify({"error": "Agent not found."}), 404
            booking.agent_id = agent_id

        booking.name = data.get("name", booking.name)
        booking.date_from = datetime.strptime(data["date_from"],
                                              "%m/%d/%Y") if "date_from" in data else booking.date_from
        booking.date_to = datetime.strptime(data["date_to"], "%m/%d/%Y") if "date_to" in data else booking.date_to
        booking.country = data.get("country", booking.country)
        booking.pax = int(data.get("pax", booking.pax))
        booking.ladies = int(data.get("ladies", booking.ladies))
        booking.men = int(data.get("men", booking.men))
        booking.children = int(data.get("children", booking.children))
        booking.teens = int(data.get("teens", booking.teens))
        booking.consultant = data.get("consultant", booking.consultant)

        # Only admins can change the user_id
        if data.get("user_id") and current_user.role == 'admin':
            booking.user_id = data.get("user_id")

        db.session.commit()
        current_app.logger.info(f"Booking {booking_id} updated successfully")

    except ValueError as e:
        db.session.rollback()
        error_msg = f"Invalid data format: {str(e)}"
        current_app.logger.error(error_msg)
        return jsonify({"error": error_msg}), 400
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error updating booking: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": error_msg}), 400

    return jsonify({"booking": booking.to_dict()})


@bookingsbp.route("/booking/import", methods=("POST",))
@token_required
def import_bookings(current_user):
    current_app.logger.info(f"User {current_user.username} attempting to import bookings")

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
                # Find agent by name or create a default agent entry if not found
                agent_name = row.get("agent")
                agent_id = row.get("agent_id")

                agent = None
                if agent_name:
                    agent = Agent.query.filter_by(name=agent_name).first()
                elif agent_id:
                    agent = Agent.query.get(agent_id)

                if not agent:
                    error_message = f"Agent not found for booking '{row.get('name')}'"
                    current_app.logger.warning(error_message)
                    errors.append(error_message)
                    error_count += 1
                    continue

                booking = Booking(
                    name=row["name"],
                    date_from=datetime.strptime(row["date_from"], "%m/%d/%Y"),
                    date_to=datetime.strptime(row["date_to"], "%m/%d/%Y"),
                    country=row["country"],
                    pax=int(row["pax"]) if row["pax"] else 0,
                    ladies=int(row["ladies"]) if row["ladies"] else 0,
                    men=int(row["men"]) if row["men"] else 0,
                    children=int(row["children"]) if row["children"] else 0,
                    teens=int(row["teens"]) if row["teens"] else 0,
                    agent_id=agent.id,
                    consultant=row["consultant"],
                    user_id=current_user.id
                )

                db.session.add(booking)
                imported_count += 1

            except Exception as e:
                error_message = f"Error on row {csv_reader.line_num}: {str(e)}"
                current_app.logger.error(error_message)
                errors.append(error_message)
                error_count += 1

        db.session.commit()
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
        db.session.rollback()
        error_msg = f"Error importing bookings: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": error_msg}), 400


@bookingsbp.route("/booking/delete/<int:booking_id>", methods=("DELETE",))
@token_required
def delete_booking(current_user, booking_id):
    current_app.logger.info(f"User {current_user.username} attempting to delete booking {booking_id}")

    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            current_app.logger.warning(f"Booking with ID {booking_id} not found")
            return jsonify({"error": "Booking not found."}), 404

        # Check if the user has permission to delete this booking
        if booking.user_id != current_user.id and current_user.role != 'admin':
            current_app.logger.warning(
                f"Unauthorized attempt to delete booking {booking_id} by {current_user.username}")
            return jsonify({"error": "Unauthorized access!"}), 403

        db.session.delete(booking)
        db.session.commit()
        current_app.logger.info(f"Booking {booking_id} deleted successfully")

    except Exception as e:
        db.session.rollback()
        error_msg = f"Error deleting booking: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": error_msg}), 400

    return jsonify({"message": "Booking deleted successfully."})