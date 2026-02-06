"""add_mode_and_reaction_settings_to_channel

Revision ID: e015cc763cf2
Revises: 
Create Date: 2026-02-06 17:13:40.348460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e015cc763cf2'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add mode column with default value 'comment' for backward compatibility
    op.add_column('channels', sa.Column('mode', sa.String(20), nullable=False, server_default='comment'))
    
    # Add reaction_settings column (JSON, nullable)
    op.add_column('channels', sa.Column('reaction_settings', sa.JSON(), nullable=True))
    
    # Update existing channels to have mode='comment' for backward compatibility
    # This is already handled by the server_default, but we can explicitly update if needed
    op.execute("UPDATE channels SET mode = 'comment' WHERE mode IS NULL OR mode = ''")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove the added columns
    op.drop_column('channels', 'reaction_settings')
    op.drop_column('channels', 'mode')
