"""
Migration to add video hosting options to Product model
Run: flask db revision -m "Add video hosting fields"
Then: flask db upgrade
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add YouTube and Vimeo ID fields
    op.add_column('product', sa.Column('youtube_id', sa.String(50), nullable=True))
    op.add_column('product', sa.Column('vimeo_id', sa.String(50), nullable=True))
    op.add_column('product', sa.Column('video_platform', sa.String(20), nullable=True, default='local'))
    op.add_column('product', sa.Column('external_video_url', sa.String(500), nullable=True))

def downgrade():
    op.drop_column('product', 'external_video_url')
    op.drop_column('product', 'video_platform')
    op.drop_column('product', 'vimeo_id')
    op.drop_column('product', 'youtube_id')