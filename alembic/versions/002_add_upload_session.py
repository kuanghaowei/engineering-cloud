"""Add upload_session table

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add upload_session table for tracking chunked uploads"""
    
    # Create upload_status_enum if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE upload_status_enum AS ENUM (
                'initializing',
                'in_progress',
                'completed',
                'failed',
                'cancelled'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create upload_sessions table
    op.execute("""
        CREATE TABLE upload_sessions (
            id UUID PRIMARY KEY,
            file_node_id UUID NOT NULL REFERENCES file_nodes(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status upload_status_enum NOT NULL DEFAULT 'initializing',
            total_size INTEGER NOT NULL,
            uploaded_size INTEGER NOT NULL DEFAULT 0,
            total_chunks INTEGER NOT NULL,
            uploaded_chunks JSON NOT NULL DEFAULT '[]',
            commit_message VARCHAR(1000),
            error_message VARCHAR(2000),
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now(),
            completed_at TIMESTAMP
        )
    """)
    
    # Create indexes
    op.create_index('ix_upload_sessions_file_node_id', 'upload_sessions', ['file_node_id'])
    op.create_index('ix_upload_sessions_user_id', 'upload_sessions', ['user_id'])


def downgrade() -> None:
    """Remove upload_session table"""
    
    # Drop indexes
    op.drop_index('ix_upload_sessions_user_id', table_name='upload_sessions')
    op.drop_index('ix_upload_sessions_file_node_id', table_name='upload_sessions')
    
    # Drop table
    op.drop_table('upload_sessions')
    
    # Note: We don't drop the enum type as it might be used elsewhere
