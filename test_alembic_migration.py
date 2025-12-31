"""
Comprehensive test script for Alembic database migrations.

This script tests:
1. Migration module loading
2. Model definitions
3. Migration upgrade
4. Migration downgrade
5. Database schema verification
"""

import sys
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr"""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr


def test_migration_module():
    """Test that migration module can be loaded"""
    print("=" * 60)
    print("TEST 1: Migration Module Loading")
    print("=" * 60)
    
    try:
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
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_model_definitions():
    """Test that all models are properly defined"""
    print("\n" + "=" * 60)
    print("TEST 2: Model Definitions")
    print("=" * 60)
    
    try:
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
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_migration_upgrade():
    """Test migration upgrade"""
    print("\n" + "=" * 60)
    print("TEST 3: Migration Upgrade")
    print("=" * 60)
    
    # First, ensure we're at base
    print("Resetting to base...")
    exit_code, stdout, stderr = run_command(["alembic", "downgrade", "base"])
    if exit_code != 0:
        print(f"✗ Failed to downgrade to base: {stderr}")
        return False
    
    # Now upgrade
    print("Upgrading to head...")
    exit_code, stdout, stderr = run_command(["alembic", "upgrade", "head"])
    if exit_code != 0:
        print(f"✗ Migration upgrade failed: {stderr}")
        return False
    
    print("✓ Migration upgrade successful")
    
    # Verify current version
    exit_code, stdout, stderr = run_command(["alembic", "current"])
    if "001 (head)" in stdout:
        print("✓ Current version is 001 (head)")
        return True
    else:
        print(f"✗ Unexpected current version: {stdout}")
        return False


def test_migration_downgrade():
    """Test migration downgrade"""
    print("\n" + "=" * 60)
    print("TEST 4: Migration Downgrade")
    print("=" * 60)
    
    # Downgrade to base
    print("Downgrading to base...")
    exit_code, stdout, stderr = run_command(["alembic", "downgrade", "base"])
    if exit_code != 0:
        print(f"✗ Migration downgrade failed: {stderr}")
        return False
    
    print("✓ Migration downgrade successful")
    
    # Verify current version
    exit_code, stdout, stderr = run_command(["alembic", "current"])
    if "001" not in stdout:
        print("✓ Successfully downgraded to base (no version)")
        return True
    else:
        print(f"✗ Still at version after downgrade: {stdout}")
        return False


def test_database_schema():
    """Test database schema after migration"""
    print("\n" + "=" * 60)
    print("TEST 5: Database Schema Verification")
    print("=" * 60)
    
    # First, upgrade to head
    print("Upgrading to head for schema verification...")
    exit_code, stdout, stderr = run_command(["alembic", "upgrade", "head"])
    if exit_code != 0:
        print(f"✗ Failed to upgrade: {stderr}")
        return False
    
    # Check tables
    print("\nVerifying tables...")
    exit_code, stdout, stderr = run_command([
        "docker", "exec", "aec_postgres",
        "psql", "-U", "aec_user", "-d", "aec_platform",
        "-c", "\\dt"
    ])
    
    if exit_code != 0:
        print(f"✗ Failed to query tables: {stderr}")
        return False
    
    expected_tables = [
        'tenants', 'users', 'projects', 'project_members',
        'repositories', 'file_nodes', 'file_versions', 'chunks',
        'workflows', 'workflow_instances', 'digital_seals',
        'alembic_version'
    ]
    
    all_found = all(table in stdout for table in expected_tables)
    if all_found:
        print(f"✓ All {len(expected_tables)} tables exist in database")
    else:
        print(f"✗ Some tables missing from database")
        return False
    
    # Check enum types
    print("\nVerifying enum types...")
    exit_code, stdout, stderr = run_command([
        "docker", "exec", "aec_postgres",
        "psql", "-U", "aec_user", "-d", "aec_platform",
        "-c", "\\dT"
    ])
    
    if exit_code != 0:
        print(f"✗ Failed to query enum types: {stderr}")
        return False
    
    expected_enums = [
        'tenant_type_enum',
        'project_role_enum',
        'node_type_enum',
        'workflow_status_enum'
    ]
    
    all_found = all(enum in stdout for enum in expected_enums)
    if all_found:
        print(f"✓ All {len(expected_enums)} enum types exist in database")
    else:
        print(f"✗ Some enum types missing from database")
        return False
    
    # Check foreign keys
    print("\nVerifying foreign key constraints...")
    exit_code, stdout, stderr = run_command([
        "docker", "exec", "aec_postgres",
        "psql", "-U", "aec_user", "-d", "aec_platform",
        "-c", "SELECT COUNT(*) FROM pg_constraint WHERE contype = 'f';"
    ])
    
    if exit_code != 0:
        print(f"✗ Failed to query foreign keys: {stderr}")
        return False
    
    # Extract count from output
    lines = stdout.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.isdigit():
            fk_count = int(line)
            if fk_count >= 15:  # We expect at least 15 foreign keys
                print(f"✓ Found {fk_count} foreign key constraints")
                return True
            else:
                print(f"✗ Expected at least 15 foreign keys, found {fk_count}")
                return False
    
    print(f"✗ Could not parse foreign key count")
    return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("ALEMBIC MIGRATION TEST SUITE")
    print("=" * 60)
    
    results = {
        "Migration Module Loading": test_migration_module(),
        "Model Definitions": test_model_definitions(),
        "Migration Upgrade": test_migration_upgrade(),
        "Migration Downgrade": test_migration_downgrade(),
        "Database Schema Verification": test_database_schema(),
    }
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nAlembic migration is properly configured and working!")
        print("\nUsage:")
        print("  alembic upgrade head    # Apply migrations")
        print("  alembic downgrade base  # Rollback all migrations")
        print("  alembic current         # Show current version")
        print("  alembic history         # Show migration history")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
