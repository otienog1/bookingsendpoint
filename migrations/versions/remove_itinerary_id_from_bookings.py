"""Remove itinerary_id from bookings (one-to-many relationship migration)

Revision ID: remove_itinerary_id
Revises: add_itinerary_id
Create Date: 2025-12-02 00:00:00.000000

This migration removes the one-to-one itinerary_id relationship from bookings.
Itineraries now reference bookings via booking_id field (one-to-many).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'remove_itinerary_id'
down_revision = 'add_itinerary_id'
branch_labels = None
depends_on = None


def upgrade():
    """Remove the itinerary_id column from bookings table."""
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        batch_op.drop_column('itinerary_id')


def downgrade():
    """Add the itinerary_id column back (for rollback purposes)."""
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('itinerary_id', sa.String(length=24), nullable=True))
