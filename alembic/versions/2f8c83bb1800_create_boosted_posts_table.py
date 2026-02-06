"""create_boosted_posts_table

Revision ID: 2f8c83bb1800
Revises: e015cc763cf2
Create Date: 2026-02-06 17:22:50.606726

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f8c83bb1800'
down_revision: Union[str, Sequence[str], None] = 'e015cc763cf2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create boosted_posts table
    op.create_table(
        'boosted_posts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('channel_id', sa.Integer(), sa.ForeignKey('channels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('post_id', sa.Integer(), nullable=False),
        sa.Column('boost_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reaction_count', sa.Integer(), nullable=False),
        sa.Column('emojis_used', sa.JSON(), nullable=False)
    )
    
    # Create unique index on (channel_id, post_id)
    op.create_index('idx_channel_post', 'boosted_posts', ['channel_id', 'post_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop the index first
    op.drop_index('idx_channel_post', table_name='boosted_posts')
    
    # Drop the table
    op.drop_table('boosted_posts')
