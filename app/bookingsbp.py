from flask import Blueprint, jsonify, request
from .booking import Booking
from . import db
import csv
from datetime import datetime

bookingsbp = Blueprint("bookingspb", __name__)


@bookingsbp.route("/booking/fetch", methods=("GET",))
def fetch_bookings():
    bookings = Booking.query.all()
    return jsonify({"bookings": [booking.to_dict() for booking in bookings]})


@bookingsbp.route("/booking/create", methods=("POST",))
def create_booking():
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
        )

        db.session.add(booking)
        db.session.commit()

    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"booking": booking.to_dict()})


@bookingsbp.route("/booking/edit/<int:booking_id>", methods=("PUT",))
def edit_booking(booking_id):

    data = request.get_json()

    try:
        booking = Booking.query.get(booking_id)

        if not booking:
            return jsonify({"error": "Booking not found."}), 404

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
def import_bookings():
    file = request.files.get("file")

    if not file or not file.filename.endswith(".csv"):
        return jsonify({"error": "Invalid file format. Please upload a CSV file."}), 400

    try:

        csv_reader = csv.DictReader(file.stream.read().decode("utf-8").splitlines())

        for row in csv_reader:
            bookings = Booking(
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
            )

            db.session.add(bookings)
            db.session.commit()

    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"message": "Bookings imported successfully."})


@bookingsbp.route("/booking/delete/<int:booking_id>", methods=("DELETE",))
def delete_booking(booking_id):
    try:
        booking = Booking.query.get(booking_id)
        if not booking:
            return jsonify({"error": "Booking not found."}), 404

        db.session.delete(booking)
        db.session.commit()

    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"message": "Booking deleted successfully."})
