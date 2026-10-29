"""Initial admissions schema."""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None

def upgrade():
    op.create_table('courses', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('source_url', sa.String(500), nullable=False, unique=True), sa.Column('title', sa.String(300), nullable=False), sa.Column('status', sa.String(40), nullable=False), sa.Column('hours', sa.String(100), nullable=False), sa.Column('content', sa.Text(), nullable=False), sa.Column('registration_url', sa.String(1000), nullable=False), sa.Column('approved', sa.Boolean(), nullable=False), sa.Column('pending', sa.JSON(), nullable=True), sa.Column('synced_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('leads', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('channel', sa.String(30), nullable=False), sa.Column('external_id', sa.String(100), nullable=False), sa.Column('name', sa.String(200), nullable=False), sa.Column('stage', sa.String(40), nullable=False), sa.Column('course_id', sa.Integer(), sa.ForeignKey('courses.id'), nullable=True), sa.Column('profile', sa.JSON(), nullable=False), sa.Column('priority', sa.Integer(), nullable=False), sa.Column('handoff', sa.Boolean(), nullable=False), sa.Column('owner', sa.String(150), nullable=False), sa.Column('notes', sa.Text(), nullable=False), sa.Column('next_action', sa.String(500), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint('channel', 'external_id'))
    op.create_table('messages', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('lead_id', sa.Integer(), sa.ForeignKey('leads.id'), nullable=False), sa.Column('external_id', sa.String(100), nullable=True), sa.Column('role', sa.String(30), nullable=False), sa.Column('text', sa.Text(), nullable=False), sa.Column('delivery', sa.String(30), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint('lead_id', 'external_id'))
    op.create_index('ix_messages_lead_id', 'messages', ['lead_id'])
    op.create_table('audit', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('actor', sa.String(100), nullable=False), sa.Column('action', sa.String(100), nullable=False), sa.Column('detail', sa.Text(), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))

def downgrade():
    for table in ('audit', 'messages', 'leads', 'courses'):
        op.drop_table(table)
