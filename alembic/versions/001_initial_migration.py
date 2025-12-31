"""Initial migration with all models

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create tenants table (enum types will be created automatically by SQLAlchemy)
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('tenant_type', sa.Enum('design', 'construction', 'owner', 'supervision', name='tenant_type_enum'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_projects_tenant_id', 'projects', ['tenant_id'])
    
    # Create project_members table
    op.create_table(
        'project_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.Enum('owner', 'editor', 'viewer', 'approver', name='project_role_enum'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_project_members_project_id', 'project_members', ['project_id'])
    op.create_index('ix_project_members_user_id', 'project_members', ['user_id'])
    
    # Create repositories table
    op.create_table(
        'repositories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('specialty', sa.String(length=100), nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_repositories_project_id', 'repositories', ['project_id'])
    
    # Create chunks table
    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_hash', sa.String(length=64), nullable=False),
        sa.Column('chunk_size', sa.Integer(), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('ref_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chunk_hash')
    )
    op.create_index('idx_chunks_hash', 'chunks', ['chunk_hash'])
    
    # Create file_nodes table
    op.create_table(
        'file_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('path', sa.String(length=2000), nullable=False),
        sa.Column('node_type', sa.Enum('file', 'directory', name='node_type_enum'), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['file_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_file_nodes_parent_id', 'file_nodes', ['parent_id'])
    op.create_index('ix_file_nodes_repository_id', 'file_nodes', ['repository_id'])
    op.create_index('idx_file_nodes_repository_path', 'file_nodes', ['repository_id', 'path'])
    
    # Create file_versions table
    op.create_table(
        'file_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_node_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('commit_hash', sa.String(length=64), nullable=False),
        sa.Column('commit_message', sa.String(length=1000), nullable=True),
        sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('parent_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('chunk_refs', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('is_locked', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['file_node_id'], ['file_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_version_id'], ['file_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('commit_hash')
    )
    op.create_index('ix_file_versions_file_node_id', 'file_versions', ['file_node_id'])
    op.create_index('ix_file_versions_author_id', 'file_versions', ['author_id'])
    op.create_index('ix_file_versions_commit_hash', 'file_versions', ['commit_hash'])
    op.create_index('idx_file_versions_file_node', 'file_versions', ['file_node_id', 'version_number'])
    
    # Add foreign key for current_version_id in file_nodes
    op.create_foreign_key(
        'fk_file_nodes_current_version_id',
        'file_nodes',
        'file_versions',
        ['current_version_id'],
        ['id'],
        ondelete='SET NULL'
    )
    
    # Create workflows table
    op.create_table(
        'workflows',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('nodes_config', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflows_project_id', 'workflows', ['project_id'])
    
    # Create workflow_instances table
    op.create_table(
        'workflow_instances',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workflow_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', 'completed', name='workflow_status_enum'), nullable=False),
        sa.Column('current_node_index', sa.Integer(), nullable=False),
        sa.Column('approval_history', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['file_version_id'], ['file_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_instances_workflow_id', 'workflow_instances', ['workflow_id'])
    op.create_index('ix_workflow_instances_file_version_id', 'workflow_instances', ['file_version_id'])
    op.create_index('idx_workflow_instances_status', 'workflow_instances', ['status', 'current_node_index'])
    
    # Create digital_seals table
    op.create_table(
        'digital_seals',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seal_name', sa.String(length=255), nullable=False),
        sa.Column('seal_image_key', sa.String(length=500), nullable=False),
        sa.Column('certificate_hash', sa.String(length=64), nullable=False),
        sa.Column('certificate_key', sa.String(length=500), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_digital_seals_user_id', 'digital_seals', ['user_id'])


def downgrade() -> None:
    # Drop tables in reverse order
    # First, drop the foreign key constraint from file_nodes to file_versions
    op.drop_constraint('fk_file_nodes_current_version_id', 'file_nodes', type_='foreignkey')
    
    # Now drop tables in reverse order
    op.drop_table('digital_seals')
    op.drop_table('workflow_instances')
    op.drop_table('workflows')
    op.drop_table('file_versions')
    op.drop_table('file_nodes')
    op.drop_table('chunks')
    op.drop_table('repositories')
    op.drop_table('project_members')
    op.drop_table('projects')
    op.drop_table('users')
    op.drop_table('tenants')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS workflow_status_enum")
    op.execute("DROP TYPE IF EXISTS node_type_enum")
    op.execute("DROP TYPE IF EXISTS project_role_enum")
    op.execute("DROP TYPE IF EXISTS tenant_type_enum")
