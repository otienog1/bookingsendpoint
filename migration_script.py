"""
Migration script to migrate existing bookings to use the new Agent model.
Run this script after creating the new Agent model and updating the Booking model.

Usage:
    flask shell
    # >>> from migration_script import migrate_bookings
    # >>> migrate_bookings()
"""
from sqlalchemy import text
from app import db
from app.agent import Agent
from app.booking import Booking
from app.user import User


def migrate_bookings():
    """
    Migrate existing bookings with string agent field to use the new Agent model with foreign key.
    """
    print("Starting migration of existing bookings to use the new Agent model...")

    # Create a connection to execute raw SQL if needed
    connection = db.engine.connect()

    try:
        # 1. Get all unique agent names from existing bookings
        # This SQL query works with the old schema where 'agent' is a string column
        result = connection.execute(text("SELECT DISTINCT agent FROM bookings"))
        unique_agents = [row[0] for row in result]

        print(f"Found {len(unique_agents)} unique agents to migrate")

        # 2. For each unique agent name, create an Agent record if it doesn't exist
        agent_mapping = {}  # Maps agent name to agent ID

        for agent_name in unique_agents:
            # Find a default user to assign as creator (preferably an admin)
            admin_user = User.query.filter_by(role='admin').first()
            if not admin_user:
                admin_user = User.query.first()  # Fallback to any user

            # Create new agent record
            agent = Agent(
                name=agent_name,
                email=f"{agent_name.lower().replace(' ', '.')}@example.com",  # Temporary email
                country="Unknown",  # Default country
                user_id=admin_user.id
            )

            db.session.add(agent)
            db.session.flush()  # Flush to get the agent ID without committing

            agent_mapping[agent_name] = agent.id
            print(f"Created agent record for '{agent_name}' with ID {agent.id}")

        # 3. Update all bookings to use the new agent_id foreign key
        # First, add the new agent_id column if it doesn't exist
        try:
            connection.execute(text("ALTER TABLE bookings ADD COLUMN agent_id INTEGER"))
            print("Added agent_id column to bookings table")
        except Exception as e:
            # Column might already exist
            print(f"Note: {str(e)}")

        # Update each booking to set the agent_id based on the agent name
        for agent_name, agent_id in agent_mapping.items():
            connection.execute(
                text(f"UPDATE bookings SET agent_id = {agent_id} WHERE agent = :agent_name"),
                {"agent_name": agent_name}
            )
            print(f"Updated bookings for agent '{agent_name}' to use agent_id {agent_id}")

        # 4. Make agent_id NOT NULL
        connection.execute(text("ALTER TABLE bookings ALTER COLUMN agent_id SET NOT NULL"))
        print("Set agent_id column to NOT NULL")

        # 5. Add foreign key constraint
        connection.execute(text(
            "ALTER TABLE bookings ADD CONSTRAINT fk_bookings_agent_id FOREIGN KEY (agent_id) REFERENCES agents(id)"
        ))
        print("Added foreign key constraint from bookings.agent_id to agents.id")

        # 6. Commit all changes
        db.session.commit()
        print("Migration completed successfully!")

    except Exception as e:
        db.session.rollback()
        print(f"Migration failed: {str(e)}")
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    print("This script should be run from within Flask shell")
    print("Usage: flask shell")
    print(">>> from migration_script import migrate_bookings")
    print(">>> migrate_bookings()")