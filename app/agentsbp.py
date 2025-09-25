from flask import Blueprint, jsonify, request
from .mongodb_models import Agent
from . import mongo
from bson import ObjectId
from .authbp import token_required
import csv

agentsbp = Blueprint("agentsbp", __name__)


@agentsbp.route("/agent/fetch", methods=("GET",))
@token_required
def fetch_agents(current_user):
    """Original agent fetch endpoint."""
    return _fetch_agents_logic(current_user)


def _fetch_agents_logic(current_user):
    """Shared logic for fetching agents."""
    # Fetch all agents or only active ones
    show_inactive = request.args.get('show_inactive', 'false').lower() == 'true'

    if show_inactive and current_user['role'] == 'admin':
        agents = Agent.get_all()
    else:
        agents = Agent.get_active()

    return jsonify({"agents": [Agent.to_dict(agent) for agent in agents]})


@agentsbp.route("/api/agent/fetch", methods=("GET",))
@token_required
def api_fetch_agents(current_user):
    """API endpoint alias for agent fetch."""
    return _fetch_agents_logic(current_user)


@agentsbp.route("/agent/<agent_id>", methods=("GET",))
@token_required
def get_agent(current_user, agent_id):
    agent = Agent.find_by_id(agent_id)

    if not agent:
        return jsonify({"error": "Agent not found."}), 404

    return jsonify({"agent": Agent.to_dict(agent)})


@agentsbp.route("/agent/create", methods=("POST",))
@token_required
def create_agent(current_user):
    data = request.get_json()

    try:
        # Check if an agent with the same email already exists
        existing_agent = Agent.find_by_email(data["email"])
        if existing_agent:
            return jsonify({"error": "An agent with this email already exists."}), 400

        agent = Agent.create_agent(
            name=data["name"],
            email=data["email"],
            country=data["country"],
            user_id=str(current_user['_id']),
            company=data.get("company"),
            phone=data.get("phone"),
            address=data.get("address"),
            notes=data.get("notes"),
            is_active=data.get("is_active", True)
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"agent": Agent.to_dict(agent)}), 201


@agentsbp.route("/agent/edit/<agent_id>", methods=("PUT",))
@token_required
def edit_agent(current_user, agent_id):
    data = request.get_json()

    try:
        agent = Agent.find_by_id(agent_id)

        if not agent:
            return jsonify({"error": "Agent not found."}), 404

        # Check if the user has permission to edit this agent
        if str(agent['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            return jsonify({"error": "Unauthorized access!"}), 403

        # Check if email is being changed and if it's already in use
        if "email" in data and data["email"] != agent['email']:
            existing_agent = Agent.find_by_email(data["email"])
            if existing_agent and str(existing_agent['_id']) != agent_id:
                return jsonify({"error": "An agent with this email already exists."}), 400

        # Prepare update data
        update_data = {}
        
        # Update agent fields
        if "name" in data:
            update_data["name"] = data["name"]
        if "company" in data:
            update_data["company"] = data["company"]
        if "email" in data:
            update_data["email"] = data["email"]
        if "phone" in data:
            update_data["phone"] = data["phone"]
        if "country" in data:
            update_data["country"] = data["country"]
        if "address" in data:
            update_data["address"] = data["address"]
        if "notes" in data:
            update_data["notes"] = data["notes"]

        # Only admins can change the active status or reassign user
        if current_user['role'] == 'admin':
            if "is_active" in data:
                update_data["is_active"] = data["is_active"]
            if "user_id" in data:
                update_data["user_id"] = ObjectId(data["user_id"])

        if update_data:
            Agent.update_one(
                {"_id": ObjectId(agent_id)},
                {"$set": update_data}
            )

        # Get updated agent
        updated_agent = Agent.find_by_id(agent_id)

    except Exception as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"agent": Agent.to_dict(updated_agent)})


@agentsbp.route("/agent/delete/<agent_id>", methods=("DELETE",))
@token_required
def delete_agent(current_user, agent_id):
    try:
        agent = Agent.find_by_id(agent_id)
        if not agent:
            return jsonify({"error": "Agent not found."}), 404

        # Check if the user has permission to delete this agent
        if str(agent['user_id']) != str(current_user['_id']) and current_user['role'] != 'admin':
            return jsonify({"error": "Unauthorized access!"}), 403

        Agent.delete_one({"_id": ObjectId(agent_id)})

    except Exception as e:
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
                existing_agent = Agent.find_by_email(row["email"])
                if existing_agent:
                    errors.append(f"Agent with email {row['email']} already exists")
                    error_count += 1
                    continue

                Agent.create_agent(
                    name=row["name"],
                    email=row["email"],
                    country=row["country"],
                    user_id=str(current_user['_id']),
                    company=row.get("company", ""),
                    phone=row.get("phone", ""),
                    address=row.get("address", ""),
                    notes=row.get("notes", ""),
                    is_active=True
                )

                imported_count += 1
            except Exception as e:
                errors.append(f"Error on row {csv_reader.line_num}: {str(e)}")
                error_count += 1

        result = {
            "message": f"{imported_count} agents imported successfully.",
            "imported": imported_count,
            "errors": error_count
        }

        if errors:
            result["error_details"] = errors

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 400