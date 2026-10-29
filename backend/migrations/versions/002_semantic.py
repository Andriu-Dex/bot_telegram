"""Semantic interaction thermometer and advisor briefing."""
from alembic import op
import sqlalchemy as sa

revision = '002'
down_revision = '001'

def upgrade():
    op.add_column('leads', sa.Column('sentiment', sa.String(30), nullable=False, server_default='interesado'))
    op.add_column('leads', sa.Column('sentiment_reason', sa.String(500), nullable=False, server_default='Primera consulta'))
    op.add_column('leads', sa.Column('summary', sa.Text(), nullable=False, server_default=''))

def downgrade():
    for column in ('summary', 'sentiment_reason', 'sentiment'):
        op.drop_column('leads', column)
