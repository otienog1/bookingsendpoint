"""
Migration script to migrate existing bookings to use the new Agent model.
This script:
1. Reads data from the CSV file to extract booking_id and agent names
2. Populates the agents table with unique agent names
3. Links bookings to agents by setting the agent_id field

Usage:
    flask shell
    # >>> from fixed_migration_script import migrate_bookings_from_csv
    # >>> migrate_bookings_from_csv()
"""
import csv
import os
from sqlalchemy import text
from app import db
from app.agent import Agent
from app.user import User


def migrate_bookings_from_csv(csv_filename="instance/bookings_to_remote_db_.csv"):
    """
    Migrate bookings data from CSV file to the database.
    The CSV file should have booking_id in the first column and agent name in the 11th column.
    """
    print(f"Starting migration of bookings from CSV file: {csv_filename}")

    # Check if the CSV file exists
    if not os.path.exists(csv_filename):
        raise FileNotFoundError(f"CSV file not found: {csv_filename}")

    # Create a connection to execute raw SQL
    connection = db.engine.connect()

    try:
        # Step 1: Read the CSV file and collect unique agent names and booking-agent mappings
        agent_names = set()  # To collect unique agent names
        booking_agent_mapping = {}  # Map booking_id to agent_name

        with open(csv_filename, 'r') as csvfile:
            csv_reader = csv.reader(csvfile)
            for row in csv_reader:
                if len(row) < 12:  # Ensure we have enough columns (agent name is in the 11th column)
                    print(f"Warning: Row has insufficient columns: {row}")
                    continue

                booking_id = row[0].strip()
                agent_name = row[10].strip()  # 11th column (index 10)

                # Skip if booking_id is not a number or agent name is empty
                if not booking_id.isdigit() or not agent_name:
                    print(f"Warning: Invalid booking_id or empty agent name: {booking_id}, {agent_name}")
                    continue

                booking_agent_mapping[int(booking_id)] = agent_name
                agent_names.add(agent_name)

        print(f"Found {len(booking_agent_mapping)} bookings with agent information")
        print(f"Found {len(agent_names)} unique agent names")

        # Step 2: Reset all existing agent_id references in bookings table to avoid FK violations
        connection.execute(text("UPDATE bookings SET agent_id = NULL"))
        print("Reset all bookings agent_id references to NULL")

        # Step 3: Make sure the agents table exists and is populated with the unique agent names
        # Find a default user to assign as creator (preferably an admin)
        admin_user = User.query.filter_by(role='admin').first()
        if not admin_user:
            admin_user = User.query.first()  # Fallback to any user

        if not admin_user:
            raise Exception("No users found in the database")

        print(f"Using user {admin_user.username} (ID: {admin_user.id}) as default agent creator")

        agent_mapping = {}  # Maps agent name to agent ID

        # First check which agents already exist
        for agent_name in agent_names:
            # Check if agent already exists
            existing_agent = Agent.query.filter_by(name=agent_name).first()

            if existing_agent:
                agent_mapping[agent_name] = existing_agent.id
                print(f"Agent '{agent_name}' already exists with ID {existing_agent.id}")
            else:
                # Create new agent record
                new_agent = Agent(
                    name=agent_name,
                    email=f"{agent_name.lower().replace(' ', '.').replace('&', 'and').replace('-', '').replace('(', '').replace(')', '')}@example.com",
                    country="Unknown",  # Default country
                    user_id=admin_user.id
                )

                db.session.add(new_agent)
                # Commit each agent individually to ensure it's in the database before we reference it
                db.session.commit()

                agent_mapping[agent_name] = new_agent.id
                print(f"Created agent record for '{agent_name}' with ID {new_agent.id}")

        # Step 4: Update agent text field in bookings for reference
        for booking_id, agent_name in booking_agent_mapping.items():
            connection.execute(
                text("UPDATE bookings SET agent = :agent_name WHERE id = :booking_id"),
                {"agent_name": agent_name, "booking_id": booking_id}
            )

        print(f"Updated agent text field for bookings")

        # Step 5: Now update each booking with the correct agent_id from our mapping
        updated_count = 0
        for booking_id, agent_name in booking_agent_mapping.items():
            agent_id = agent_mapping.get(agent_name)
            if agent_id:
                try:
                    connection.execute(
                        text("UPDATE bookings SET agent_id = :agent_id WHERE id = :booking_id"),
                        {"agent_id": agent_id, "booking_id": booking_id}
                    )
                    updated_count += 1
                except Exception as e:
                    print(f"Failed to update booking {booking_id}: {str(e)}")
            else:
                print(f"Warning: No agent found for '{agent_name}' (booking ID: {booking_id})")

        print(f"Updated {updated_count} bookings with agent_id references")

        # Commit all remaining changes
        connection.commit()
        print("Migration completed successfully!")

    except Exception as e:
        db.session.rollback()
        connection.rollback()
        print(f"Migration failed: {str(e)}")
        raise
    finally:
        connection.close()


def check_migration_status():
    """
    Check the status of the migration - show counts of bookings with and without agent_id.
    """
    connection = db.engine.connect()

    try:
        # Count total bookings
        result = connection.execute(text("SELECT COUNT(*) FROM bookings"))
        total_bookings = result.scalar()

        # Count bookings with agent_id
        result = connection.execute(text("SELECT COUNT(*) FROM bookings WHERE agent_id IS NOT NULL"))
        bookings_with_agent_id = result.scalar()

        # Count bookings without agent_id
        result = connection.execute(text("SELECT COUNT(*) FROM bookings WHERE agent_id IS NULL"))
        bookings_without_agent_id = result.scalar()

        # Count unique agent names
        result = connection.execute(text("SELECT COUNT(DISTINCT agent) FROM bookings"))
        unique_agent_names = result.scalar()

        # Count agents in the agents table
        result = connection.execute(text("SELECT COUNT(*) FROM agents"))
        agent_records = result.scalar()

        # Check if there are any bookings with invalid agent_id references
        result = connection.execute(text("""
            SELECT COUNT(*) 
            FROM bookings b
            LEFT JOIN agents a ON b.agent_id = a.id
            WHERE b.agent_id IS NOT NULL AND a.id IS NULL
        """))
        invalid_agent_references = result.scalar()

        print(f"Migration Status Report:")
        print(f"------------------------")
        print(f"Total bookings: {total_bookings}")
        percentage_with_agent = (bookings_with_agent_id / total_bookings * 100) if total_bookings > 0 else 0
        percentage_without_agent = (bookings_without_agent_id / total_bookings * 100) if total_bookings > 0 else 0
        print(f"Bookings with agent_id: {bookings_with_agent_id} ({percentage_with_agent:.1f}%)")
        print(f"Bookings without agent_id: {bookings_without_agent_id} ({percentage_without_agent:.1f}%)")
        print(f"Unique agent names in bookings table: {unique_agent_names}")
        print(f"Agent records in agents table: {agent_records}")
        print(f"Bookings with invalid agent_id references: {invalid_agent_references}")

    except Exception as e:
        print(f"Status check failed: {str(e)}")
    finally:
        connection.close()


def find_problematic_bookings():
    """
    Identify bookings that may be causing foreign key constraint violations.
    """
    connection = db.engine.connect()

    try:
        # Find bookings with agent_id that doesn't exist in agents table
        result = connection.execute(text("""
            SELECT b.id, b.agent_id, b.agent 
            FROM bookings b
            LEFT JOIN agents a ON b.agent_id = a.id
            WHERE b.agent_id IS NOT NULL AND a.id IS NULL
        """))

        print("Bookings with invalid agent_id references:")
        print("------------------------------------------")
        problem_found = False
        for row in result:
            problem_found = True
            print(f"Booking ID: {row[0]}, Invalid agent_id: {row[1]}, Agent name: {row[2]}")

        if not problem_found:
            print("No problematic bookings found.")

    except Exception as e:
        print(f"Problematic bookings check failed: {str(e)}")
    finally:
        connection.close()


def reset_agent_references():
    """
    Reset all agent_id references in the bookings table to NULL.
    Use this as a last resort if you need to start over.
    """
    connection = db.engine.connect()

    try:
        connection.execute(text("UPDATE bookings SET agent_id = NULL"))
        db.session.commit()
        print("Reset all agent_id references to NULL")
    except Exception as e:
        db.session.rollback()
        print(f"Reset failed: {str(e)}")
    finally:
        connection.close()


if __name__ == "__main__":
    print("This script should be run from within Flask shell")
    print("Usage: flask shell")
    print(">>> from fixed_migration_script import migrate_bookings_from_csv, check_migration_status, find_problematic_bookings")
    print(">>> migrate_bookings_from_csv()")
    print(">>> check_migration_status()")
    print(">>> find_problematic_bookings()")