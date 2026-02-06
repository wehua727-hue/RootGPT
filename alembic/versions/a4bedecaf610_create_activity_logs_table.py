"""create_activity_logs_table

Revision ID: a4bedecaf610
Revises: 2f8c83bb1800
Create Date: 2026-02-06 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4bedecaf610'
down_revision: Union[str, Sequence[str], None] = '2f8c83bb1800'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create activity_logs table
    op.create_table(
        'activity_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('channel_id', sa.Integer(), sa.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=True),
        sa.Column('activity_type', sa.String(50), nullable=False),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False)
    )
    
    # Create index on (channel_id, timestamp) for efficient queries
    op.create_index('idx_channel_timestamp', 'activity_logs', ['channel_id', 'timestamp'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the index first
    op.drop_index('idx_channel_timestamp', table_name='activity_logs')
    
    # Drop the table
    op.drop_table('activity_logs')
