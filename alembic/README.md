# Alembic Database Migrations

This directory contains Alembic database migration scripts for the AEC Collaboration Platform.

## Overview

Alembic is a database migration tool for SQLAlchemy. It allows you to:
- Track database schema changes over time
- Apply migrations to upgrade the database
- Rollback migrations to downgrade the database
- Generate migration scripts automatically from model changes

## Configuration

### Files

- `alembic.ini` - Main Alembic configuration file
- `env.py` - Migration environment configuration
- `versions/` - Directory containing migration scripts
  - `001_initial_migration.py` - Initial database schema

### Database Connection

The database connection URL is automatically loaded from the application configuration (`app/config.py`) which reads from the `.env` file. The connection string is converted from async (asyncpg) to sync (psycopg2) format for Alembic compatibility.

## Usage

### Check Current Migration Version

```bash
alembic current
```

### View Migration History

```bash
alembic history
```

### Apply All Pending Migrations

```bash
alembic upgrade head
```

### Rollback All Migrations

```bash
alembic downgrade base
```

### Rollback One Migration

```bash
alembic downgrade -1
```

### Generate New Migration (Auto-detect Changes)

```bash
alembic revision --autogenerate -m "Description of changes"
```

### Generate Empty Migration

```bash
alembic revision -m "Description of changes"
```

## Initial Migration (001)

The initial migration creates all core tables:

### Tables Created

1. **tenants** - Organization/tenant entities
2. **users** - User accounts
3. **projects** - Project containers
4. **project_members** - Project membership and roles
5. **repositories** - Specialty repositories within projects
6. **file_nodes** - File and directory nodes
7. **file_versions** - File version history
8. **chunks** - File content chunks (content-addressable storage)
9. **workflows** - Workflow definitions
10. **workflow_instances** - Workflow execution instances
11. **digital_seals** - Digital signature seals

### Enum Types Created

1. **tenant_type_enum** - design, construction, owner, supervision
2. **project_role_enum** - owner, editor, viewer, approver
3. **node_type_enum** - file, directory
4. **workflow_status_enum** - pending, approved, rejected, completed

### Foreign Key Constraints

The migration establishes proper referential integrity with foreign key constraints:

- Users belong to tenants
- Projects belong to tenants
- Project members link users to projects
- Repositories belong to projects
- File nodes belong to repositories and can have parent nodes
- File versions belong to file nodes and have authors
- Workflows belong to projects
- Workflow instances link workflows to file versions
- Digital seals belong to users

### Indexes

Performance indexes are created on:
- Foreign key columns
- Frequently queried columns (chunk_hash, commit_hash)
- Composite indexes for common query patterns

## Testing

Run the comprehensive migration test suite:

```bash
python test_alembic_migration.py
```

This tests:
1. Migration module loading
2. Model definitions
3. Migration upgrade
4. Migration downgrade
5. Database schema verification

## Troubleshooting

### Migration Already Applied

If you see "Target database is not up to date", check the current version:

```bash
alembic current
```

### Migration Conflicts

If you have conflicts between migrations, you may need to:

1. Check the migration history: `alembic history`
2. Manually resolve conflicts in the migration files
3. Test with downgrade/upgrade cycle

### Database Connection Issues

Ensure:
1. PostgreSQL is running: `docker compose ps`
2. Environment variables are set correctly in `.env`
3. Database credentials match docker-compose.yml

### Circular Dependencies

The initial migration handles circular dependencies between `file_nodes` and `file_versions` by:
1. Creating both tables first
2. Adding the foreign key constraint from `file_nodes.current_version_id` after both tables exist
3. Dropping this constraint first during downgrade

## Best Practices

1. **Always test migrations** on a development database before production
2. **Backup your database** before applying migrations in production
3. **Review auto-generated migrations** - they may need manual adjustments
4. **Use descriptive migration messages** to make history clear
5. **Test both upgrade and downgrade** paths
6. **Keep migrations small and focused** on specific changes
7. **Never edit applied migrations** - create new ones instead

## Development Workflow

When making model changes:

1. Update the SQLAlchemy models in `app/models/`
2. Generate a new migration:
   ```bash
   alembic revision --autogenerate -m "Add new field to User model"
   ```
3. Review the generated migration in `alembic/versions/`
4. Test the migration:
   ```bash
   alembic upgrade head
   alembic downgrade -1
   alembic upgrade head
   ```
5. Commit both the model changes and migration script

## Production Deployment

For production deployments:

1. Backup the database
2. Apply migrations during a maintenance window
3. Monitor for errors
4. Have a rollback plan ready
5. Test the application after migration

```bash
# Production migration command
alembic upgrade head
```

## References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
