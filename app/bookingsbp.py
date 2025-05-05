from flask import Blueprint, jsonify, request
from .booking import Booking
from . import db
from .authbp import token_required
import csv
from datetime import datetime

bookingsbp = Blueprint("bookingsbp", __name__)  # Fixed the name here (was "bookingspb")


@bookingsbp.route("/booking/fetch", methods=("GET",))
def fetch_bookings():
    bookings = Booking.query.all()
    return jsonify({"bookings": [booking.to_dict() for booking in bookings]})


@bookingsbp.route("/booking/create", methods=("POST",))
@token_required
def create_booking(current_user):  # Added current_user parameter
    data = request.get_json()

    try:
        # Use current_user.id if user_id is not provided in the request
        user_id = data.get("user_id", current_user.id)

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
            agent=data["agent"],
            consultant=data["consultant"],
            user_id=user_id
        )

        db.session.add(booking)
        db.session.commit()

    except Exception as e:
        db.session.rollback()  # Rollback transaction on error
        return jsonify({"error": str(e)}), 400

    return jsonify({"booking": booking.to_dict()})


@bookingsbp.route("/booking/edit/<int:booking_id>", methods=("PUT",))
@token_required
def edit_booking(current_user, booking_id):  # Added current_user parameter
    data = request.get_json()

    try:
        booking = Booking.query.get(booking_id)

        if not booking:
            return jsonify({"error": "Booking not found."}), 404

        # Check if the user has permission to edit this booking
        if booking.user_id != current_user.id and current_user.role != 'admin':
            return jsonify({"error": "Unauthorized access!"}), 403

        booking.name = data.get("name", booking.name)
        booking.date_from = datetime.strptime(data["date_from"], "%m/%d/%Y")
        booking.date_to = datetime.strptime(data["date_to"], "%m/%d/%Y")
        booking.country = data.get("country", booking.country)
        booking.pax = int(data.get("pax", booking.pax))
        booking.ladies = int(data.get("ladies", booking.ladies))
        booking.men = int(data.get("men", booking.men))
        booking.children = int(data.get("children", booking.children))
        booking.teens = int(data.get("teens", booking.teens))
        booking.agent = data.get("agent", booking.agent)
        booking.consultant = data.get("consultant", booking.consultant)

        # Only admins can change the user_id
        if data.get("user_id") and current_user.role == 'admin':
            booking.user_id = data.get("user_id")

        db.session.commit()

    except Exception as e:
        db.session.rollback()  # Rollback transaction on error
        return jsonify({"error": str(e)}), 400

    return jsonify({"booking": booking.to_dict()})


@bookingsbp.route("/booking/import", methods=("POST",))
@token_required
def import_bookings(current_user):  # Added current_user parameter
    file = request.files.get("file")

    if not file or not file.filename.endswith(".csv"):
        return jsonify({"error": "Invalid file format. Please upload a CSV file."}), 400

    try:
        csv_reader = csv.DictReader(file.stream.read().decode("utf-8").splitlines())
        imported_count = 0

        for row in csv_reader:
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
                agent=row["agent"],
                consultant=row["consultant"],
                user_id=current_user.id  # Set the current user as the owner
            )

            db.session.add(booking)
            imported_count += 1

        db.session.commit()
        return jsonify({"message": f"{imported_count} bookings imported successfully."})

    except Exception as e:
        db.session.rollback()  # Rollback transaction on error
        return jsonify({"error": str(e)}), 400


@bookingsbp.route("/booking/delete/<int:booking_id>", methods=("DELETE",))
@token_required
def delete_booking(current_user, booking_id):  # Added current_user parameter
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
        db.session.rollback()  # Rollback transaction on error
        return jsonify({"error": str(e)}), 400

    return jsonify({"message": "Booking deleted successfully."})