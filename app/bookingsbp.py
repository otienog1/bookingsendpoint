from flask import Blueprint, jsonify, request
from .booking import Booking
from . import db
import csv
from datetime import datetime
from .authbp import token_required

bookingsbp = Blueprint("bookingspb", __name__)


@bookingsbp.route("/booking/fetch", methods=("GET",))
@token_required
def fetch_bookings(current_user):
    bookings = Booking.query.all()
    return jsonify({"bookings": [booking.to_dict() for booking in bookings]})


@bookingsbp.route("/booking/create", methods=("POST",))
@token_required
def create_booking(current_user):
    data = request.get_json()

    try:
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
            user_id=current_user.id  # Add the user_id from the current user
        )

        db.session.add(booking)
        db.session.commit()

    except Exception as e:
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

        # Optional: Check if the user has permission to edit this booking
        if booking.user_id != current_user.id and current_user.role != 'admin':
            return jsonify({"error": "You don't have permission to edit this booking."}), 403

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

        db.session.commit()

    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"booking": booking.to_dict()})


@bookingsbp.route("/booking/import", methods=("POST",))
@token_required
def import_bookings(current_user):
    # Only allow admins to import bookings
    if current_user.role != 'admin':
        return jsonify({"error": "Unauthorized access!"}), 403

    if 'file' not in request.files:
        return jsonify({"error": "No file provided."}), 400

    file = request.files.get("file")

    if not file or not file.filename.endswith(".csv"):
        return jsonify({"error": "Invalid file format. Please upload a CSV file."}), 400

    try:
        # Read the CSV content
        content = file.stream.read().decode("utf-8").splitlines()
        csv_reader = csv.DictReader(content)

        success_count = 0
        error_rows = []

        for index, row in enumerate(csv_reader, start=2):  # Start from 2 to account for header row
            try:
                # Validate required fields
                required_fields = ["name", "date_from", "date_to", "country", "pax", "ladies", "male", "children","agent", "consultant", "user_id"]
                for field in required_fields:
                    if field not in row or not row[field]:
                        raise ValueError(f"Missing required field: {field}")

                # Parse dates with error handling
                try:
                    date_from = datetime.strptime(row["date_from"], "%m/%d/%Y")
                    date_to = datetime.strptime(row["date_to"], "%m/%d/%Y")
                except ValueError:
                    raise ValueError("Invalid date format. Use MM/DD/YYYY format.")

                # Handle numeric fields safely
                pax = int(row["pax"]) if row.get("pax") and row["pax"].strip() else 0
                ladies = int(row["ladies"]) if row.get("ladies") and row["ladies"].strip() else 0
                men = int(row["men"]) if row.get("men") and row["men"].strip() else 0
                children = int(row["children"]) if row.get("children") and row["children"].strip() else 0
                teens = int(row["teens"]) if row.get("teens") and row["teens"].strip() else 0

                # Create and add the booking
                booking = Booking(
                    name=row["name"],
                    date_from=date_from,
                    date_to=date_to,
                    country=row["country"],
                    pax=pax,
                    ladies=ladies,
                    men=men,
                    children=children,
                    teens=teens,
                    agent=row["agent"],
                    consultant=row["consultant"],
                    user_id=current_user.id
                )

                db.session.add(booking)
                # Commit each booking individually to identify problematic rows
                db.session.commit()
                success_count += 1

            except Exception as row_error:
                # Roll back the current transaction
                db.session.rollback()
                error_rows.append({
                    "row": index,
                    "error": str(row_error)
                })
                # Continue processing other rows
                continue

        # If we have both successes and failures
        if success_count > 0 and error_rows:
            return jsonify({
                "message": f"Partially imported: {success_count} bookings imported successfully.",
                "errors": error_rows
            }), 207  # 207 Multi-Status

        # If all failed
        elif error_rows and success_count == 0:
            return jsonify({
                "error": "No bookings imported due to errors",
                "errors": error_rows
            }), 400

        # If all succeeded
        else:
            return jsonify({
                "message": f"Successfully imported {success_count} bookings."
            }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error importing CSV: {str(e)}"}), 400


@bookingsbp.route("/booking/delete/<int:booking_id>", methods=("DELETE",))
@token_required
def delete_booking(current_user, booking_id):
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found."}), 404

        # Allow users to delete their own bookings or admins to delete any booking
        if booking.user_id != current_user.id and current_user.role != 'admin':
            return jsonify({"error": "You don't have permission to delete this booking."}), 403

        db.session.delete(booking)
        db.session.commit()

    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"message": "Booking deleted successfully."})