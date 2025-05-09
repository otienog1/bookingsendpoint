from flask import Blueprint, jsonify, request
from .booking import Booking
from .agent import Agent
from . import db
from .authbp import token_required
import csv
from datetime import datetime

bookingsbp = Blueprint("bookingsbp", __name__)


@bookingsbp.route("/booking/fetch", methods=("GET",))
@token_required
def fetch_bookings(current_user):
    # Filter options
    agent_id = request.args.get('agent_id')
    country = request.args.get('country')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

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
        except ValueError:
            pass
    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%m/%d/%Y")
            query = query.filter(Booking.date_to <= to_date)
        except ValueError:
            pass

    # Non-admin users can only see their own bookings
    if current_user.role != 'admin':
        query = query.filter(Booking.user_id == current_user.id)

    bookings = query.all()
    return jsonify({"bookings": [booking.to_dict() for booking in bookings]})


@bookingsbp.route("/booking/create", methods=("POST",))
@token_required
def create_booking(current_user):
    data = request.get_json()

    try:
        # Use current_user.id if user_id is not provided in the request
        user_id = data.get("user_id", current_user.id)

        # Verify the agent exists
        agent_id = data["agent_id"]
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({"error": "Agent not found."}), 404

        # Only admins can create bookings for other users
        if user_id != current_user.id and current_user.role != 'admin':
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

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

    return jsonify({"booking": booking.to_dict()})


@bookingsbp.route("/booking/edit/<int:booking_id>", methods=("PUT",))
@token_required
def edit_booking(current_user, booking_id):
    data = request.get_json()

    try:
        booking = Booking.query.get(booking_id)

        if not booking:
            return jsonify({"error": "Booking not found."}), 404

        # Check if the user has permission to edit this booking
        if booking.user_id != current_user.id and current_user.role != 'admin':
            return jsonify({"error": "Unauthorized access!"}), 403

        # Verify the agent exists if agent_id is being changed
        if "agent_id" in data:
            agent_id = data["agent_id"]
            agent = Agent.query.get(agent_id)
            if not agent:
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

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

    return jsonify({"booking": booking.to_dict()})


@bookingsbp.route("/booking/import", methods=("POST",))
@token_required
def import_bookings(current_user):
    file = request.files.get("file")

    if not file or not file.filename.endswith(".csv"):
        return jsonify({"error": "Invalid file format. Please upload a CSV file."}), 400

    try:
        csv_reader = csv.DictReader(file.stream.read().decode("utf-8").splitlines())
        imported_count = 0
        error_count = 0
        errors = []

        for row in csv_reader:
            try:
                # Find agent by name or create a default agent entry if not found
                agent_name = row["agent"]
                agent = Agent.query.filter_by(name=agent_name).first()

                if not agent:
                    # If using agent_id in CSV, try to find by ID
                    agent_id = row.get("agent_id")
                    if agent_id:
                        agent = Agent.query.get(agent_id)

                    # If still not found, report error
                    if not agent:
                        errors.append(f"Agent '{agent_name}' not found for booking '{row['name']}'")
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
                errors.append(f"Error on row {csv_reader.line_num}: {str(e)}")
                error_count += 1

        db.session.commit()

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
        return jsonify({"error": str(e)}), 400


@bookingsbp.route("/booking/delete/<int:booking_id>", methods=("DELETE",))
@token_required
def delete_booking(current_user, booking_id):
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found."}), 404

        # Check if the user has permission to delete this booking
        if booking.user_id != current_user.id and current_user.role != 'admin':
            return jsonify({"error": "Unauthorized access!"}), 403

        db.session.delete(booking)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

    return jsonify({"message": "Booking deleted successfully."})