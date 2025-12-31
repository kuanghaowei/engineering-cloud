"""Test script to verify migration can be loaded"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    # Import the migration module
    import importlib.util
    migration_path = Path(__file__).resolve().parent / "alembic" / "versions" / "001_initial_migration.py"
    spec = importlib.util.spec_from_file_location("migration", migration_path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    
    print("✓ Migration module loaded successfully")
    print(f"  Revision: {migration.revision}")
    print(f"  Down revision: {migration.down_revision}")
    
    # Check that upgrade and downgrade functions exist
    assert hasattr(migration, 'upgrade'), "Missing upgrade function"
    assert hasattr(migration, 'downgrade'), "Missing downgrade function"
    print("✓ Migration functions defined")
    
    # Import all models to verify they're properly defined
    from app.models import (
        Base,
        Tenant,
        User,
        Project,
        ProjectMember,
        Repository,
        FileNode,
        FileVersion,
        Chunk,
        Workflow,
        WorkflowInstance,
        DigitalSeal,
    )
    
    print("✓ All models imported successfully")
    
    # Verify Base metadata contains all tables
    table_names = [table.name for table in Base.metadata.tables.values()]
    expected_tables = [
        'tenants',
        'users',
        'projects',
        'project_members',
        'repositories',
        'file_nodes',
        'file_versions',
        'chunks',
        'workflows',
        'workflow_instances',
        'digital_seals',
    ]
    
    for table in expected_tables:
        assert table in table_names, f"Missing table: {table}"
    
    print(f"✓ All {len(expected_tables)} tables defined in metadata")
    print(f"  Tables: {', '.join(sorted(table_names))}")
    
    # Verify foreign key relationships
    print("\n✓ Verifying foreign key constraints...")
    
    # Check some key relationships
    users_table = Base.metadata.tables['users']
    assert 'tenant_id' in [fk.parent.name for fk in users_table.foreign_keys]
    print("  - users.tenant_id → tenants.id")
    
    projects_table = Base.metadata.tables['projects']
    assert 'tenant_id' in [fk.parent.name for fk in projects_table.foreign_keys]
    print("  - projects.tenant_id → tenants.id")
    
    file_versions_table = Base.metadata.tables['file_versions']
    fk_names = [fk.parent.name for fk in file_versions_table.foreign_keys]
    assert 'file_node_id' in fk_names
    assert 'author_id' in fk_names
    print("  - file_versions.file_node_id → file_nodes.id")
    print("  - file_versions.author_id → users.id")
    
    print("\n✅ All migration and model checks passed!")
    print("\nNote: Database connection not tested (requires running PostgreSQL)")
    print("To apply migrations, ensure PostgreSQL is running and execute:")
    print("  source venv/bin/activate && alembic upgrade head")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
