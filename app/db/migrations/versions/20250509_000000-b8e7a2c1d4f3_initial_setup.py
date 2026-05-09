"""Initial migration setup.

This migration serves as the starting point for database versioning.
No tables are created yet - subsequent migrations will define the schema.
Custom PostgreSQL types and extensions can be added here as needed.

Revision ID: b8e7a2c1d4f3
Revises: 
Create Date: 2025-05-09 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b8e7a2c1d4f3"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Perform upgrade operations.

    This migration is intentionally empty as it serves only to establish
    the Alembic versioning baseline. Future migrations will create tables.
    """
    # Example: Enable required extensions if needed
    # op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    # op.execute("CREATE EXTENSION IF NOT EXISTS \"pgcrypto\"")

    # Typically you would create tables here, but we're starting with an empty schema
    # Future migrations will add tables using op.create_table() etc.
    pass


def downgrade() -> None:
    """
    Perform downgrade operations.

    Since this is an initial empty migration, downgrade does nothing.
    """
    pass
