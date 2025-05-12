from flask import Blueprint, jsonify, request
from .agent import Agent
from . import db
from .authbp import token_required
import csv

agentsbp = Blueprint("agentsbp", __name__)


@agentsbp.route("/agent/fetch", methods=("GET",))
@token_required
def fetch_agents(current_user):
    # Fetch all agents or only active ones
    show_inactive = request.args.get('show_inactive', 'false').lower() == 'true'

    if show_inactive and current_user.role == 'admin':
        agents = Agent.query.all()
    else:
        agents = Agent.query.filter_by(is_active=True).all()

    return jsonify({"agents": [agent.to_dict() for agent in agents]})


@agentsbp.route("/agent/<int:agent_id>", methods=("GET",))
@token_required
def get_agent(current_user, agent_id):
    agent = Agent.query.get(agent_id)

    if not agent:
        return jsonify({"error": "Agent not found."}), 404

    return jsonify({"agent": agent.to_dict()})


@agentsbp.route("/agent/create", methods=("POST",))
@token_required
def create_agent(current_user):
    data = request.get_json()

    try:
        # Check if an agent with the same email already exists
        existing_agent = Agent.query.filter_by(email=data["email"]).first()
        if existing_agent:
            return jsonify({"error": "An agent with this email already exists."}), 400

        agent = Agent(
            name=data["name"],
            company=data.get("company"),
            email=data["email"],
            phone=data.get("phone"),
            country=data["country"],
            address=data.get("address"),
            notes=data.get("notes"),
            is_active=data.get("is_active", True),
            user_id=current_user.id
        )

        db.session.add(agent)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

    return jsonify({"agent": agent.to_dict()}), 201


@agentsbp.route("/agent/edit/<int:agent_id>", methods=("PUT",))
@token_required
def edit_agent(current_user, agent_id):
    data = request.get_json()

    try:
        agent = Agent.query.get(agent_id)

        if not agent:
            return jsonify({"error": "Agent not found."}), 404

        # Check if the user has permission to edit this agent
        if agent.user_id != current_user.id and current_user.role != 'admin':
            return jsonify({"error": "Unauthorized access!"}), 403

        # Check if email is being changed and if it's already in use
        if "email" in data and data["email"] != agent.email:
            existing_agent = Agent.query.filter_by(email=data["email"]).first()
            if existing_agent:
                return jsonify({"error": "An agent with this email already exists."}), 400

        # Update agent fields
        agent.name = data.get("name", agent.name)
        agent.company = data.get("company", agent.company)
        agent.email = data.get("email", agent.email)
        agent.phone = data.get("phone", agent.phone)
        agent.country = data.get("country", agent.country)
        agent.address = data.get("address", agent.address)
        agent.notes = data.get("notes", agent.notes)

        # Only admins can change the active status or reassign user
        if current_user.role == 'admin':
            if "is_active" in data:
                agent.is_active = data["is_active"]
            if "user_id" in data:
                agent.user_id = data["user_id"]

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

    return jsonify({"agent": agent.to_dict()})


@agentsbp.route("/agent/delete/<int:agent_id>", methods=("DELETE",))
@token_required
def delete_agent(current_user, agent_id):
    try:
        agent = Agent.query.get(agent_id)
        if not agent:
            return jsonify({"error": "Agent not found."}), 404

        # Check if the user has permission to delete this agent
        if agent.user_id != current_user.id and current_user.role != 'admin':
            return jsonify({"error": "Unauthorized access!"}), 403

        db.session.delete(agent)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400

    return jsonify({"message": "Agent deleted successfully."})


@agentsbp.route("/agent/import", methods=("POST",))
@token_required
def import_agents(current_user):
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
                # Check if agent with this email already exists
                existing_agent = Agent.query.filter_by(email=row["email"]).first()
                if existing_agent:
                    errors.append(f"Agent with email {row['email']} already exists")
                    error_count += 1
                    continue

                agent = Agent(
                    name=row["name"],
                    company=row.get("company", ""),
                    email=row["email"],
                    phone=row.get("phone", ""),
                    country=row["country"],
                    address=row.get("address", ""),
                    notes=row.get("notes", ""),
                    is_active=True,
                    user_id=current_user.id
                )

                db.session.add(agent)
                imported_count += 1
            except Exception as e:
                errors.append(f"Error on row {csv_reader.line_num}: {str(e)}")
                error_count += 1

        db.session.commit()

        result = {
            "message": f"{imported_count} agents imported successfully.",
            "imported": imported_count,
            "errors": error_count
        }

        if errors:
            result["error_details"] = errors

        return jsonify(result)

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400