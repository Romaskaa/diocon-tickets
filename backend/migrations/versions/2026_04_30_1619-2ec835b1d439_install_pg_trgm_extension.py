"""install_pg_trgm_extension

Revision ID: 2ec835b1d439
Revises: 7b4a3734a94d
Create Date: 2026-04-30 16:19:33.301541

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ec835b1d439'
down_revision: Union[str, Sequence[str], None] = '7b4a3734a94d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
