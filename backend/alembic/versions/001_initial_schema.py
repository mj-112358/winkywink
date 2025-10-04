"""initial schema with event_id and indexes

Revision ID: 001
Revises:
Create Date: 2025-01-10 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create orgs table
    op.create_table('orgs',
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('org_id')
    )

    # Create stores_extended table
    op.create_table('stores_extended',
        sa.Column('store_id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('timezone', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.org_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('store_id')
    )
    op.create_index(op.f('ix_stores_extended_org_id'), 'stores_extended', ['org_id'], unique=False)

    # Create cameras_extended table with is_entrance column
    op.create_table('cameras_extended',
        sa.Column('camera_id', sa.String(), nullable=False),
        sa.Column('store_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('is_entrance', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rtsp_url', sa.String(), nullable=True),
        sa.Column('capabilities', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('config', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['store_id'], ['stores_extended.store_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('camera_id')
    )
    op.create_index(op.f('ix_cameras_extended_store_id'), 'cameras_extended', ['store_id'], unique=False)
    # GIN index for JSONB config queries
    op.execute('CREATE INDEX idx_cameras_config_gin ON cameras_extended USING gin(config)')

    # Create users table
    op.create_table('users',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('store_id', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.org_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['store_id'], ['stores_extended.store_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_org_id'), 'users', ['org_id'], unique=False)
    op.create_index(op.f('ix_users_store_id'), 'users', ['store_id'], unique=False)

    # Create edge_keys table
    op.create_table('edge_keys',
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('store_id', sa.String(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['org_id'], ['orgs.org_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['store_id'], ['stores_extended.store_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('key')
    )
    op.create_index(op.f('ix_edge_keys_org_id'), 'edge_keys', ['org_id'], unique=False)
    op.create_index(op.f('ix_edge_keys_store_id'), 'edge_keys', ['store_id'], unique=False)

    # Create events table with event_id for idempotency
    op.create_table('events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(), nullable=False),
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('store_id', sa.String(), nullable=False),
        sa.Column('camera_id', sa.String(), nullable=False),
        sa.Column('person_key', sa.String(), nullable=True),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Critical indexes for events table
    op.create_index('idx_events_event_id', 'events', ['event_id'], unique=True)
    op.create_index('idx_events_store_ts', 'events', ['store_id', 'ts'], unique=False)
    op.create_index('idx_events_store_type_ts', 'events', ['store_id', 'type', 'ts'], unique=False)
    op.create_index('idx_events_store_camera_person_ts', 'events', ['store_id', 'camera_id', 'person_key', 'ts'], unique=False)

    # GIN index for JSONB payload queries
    op.execute('CREATE INDEX idx_events_payload_gin ON events USING gin(payload)')

    # Regular indexes
    op.create_index(op.f('ix_events_camera_id'), 'events', ['camera_id'], unique=False)
    op.create_index(op.f('ix_events_org_id'), 'events', ['org_id'], unique=False)
    op.create_index(op.f('ix_events_person_key'), 'events', ['person_key'], unique=False)
    op.create_index(op.f('ix_events_store_id'), 'events', ['store_id'], unique=False)
    op.create_index(op.f('ix_events_ts'), 'events', ['ts'], unique=False)
    op.create_index(op.f('ix_events_type'), 'events', ['type'], unique=False)

    # Create aggregations table
    op.create_table('aggregations',
        sa.Column('org_id', sa.String(), nullable=False),
        sa.Column('store_id', sa.String(), nullable=False),
        sa.Column('metric', sa.String(), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('granularity', sa.String(), nullable=True),
        sa.Column('payload', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('org_id', 'store_id', 'metric', 'period_start')
    )


def downgrade() -> None:
    op.drop_table('aggregations')

    op.drop_index(op.f('ix_events_type'), table_name='events')
    op.drop_index(op.f('ix_events_ts'), table_name='events')
    op.drop_index(op.f('ix_events_store_id'), table_name='events')
    op.drop_index(op.f('ix_events_person_key'), table_name='events')
    op.drop_index(op.f('ix_events_org_id'), table_name='events')
    op.drop_index(op.f('ix_events_camera_id'), table_name='events')
    op.execute('DROP INDEX IF EXISTS idx_events_payload_gin')
    op.drop_index('idx_events_store_camera_person_ts', table_name='events')
    op.drop_index('idx_events_store_type_ts', table_name='events')
    op.drop_index('idx_events_store_ts', table_name='events')
    op.drop_index('idx_events_event_id', table_name='events')
    op.drop_table('events')

    op.drop_index(op.f('ix_edge_keys_store_id'), table_name='edge_keys')
    op.drop_index(op.f('ix_edge_keys_org_id'), table_name='edge_keys')
    op.drop_table('edge_keys')

    op.drop_index(op.f('ix_users_store_id'), table_name='users')
    op.drop_index(op.f('ix_users_org_id'), table_name='users')
    op.drop_table('users')

    op.execute('DROP INDEX IF EXISTS idx_cameras_config_gin')
    op.drop_index(op.f('ix_cameras_extended_store_id'), table_name='cameras_extended')
    op.drop_table('cameras_extended')

    op.drop_index(op.f('ix_stores_extended_org_id'), table_name='stores_extended')
    op.drop_table('stores_extended')

    op.drop_table('orgs')
