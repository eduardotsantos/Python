"""
Migration script to convert existing database to multitenant structure.
Run this script once to add tenant support to existing data.

Usage:
    python migrate_to_multitenant.py
"""
import os
import sys
import sqlite3
from datetime import datetime, date

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def migrate_database():
    """Migrate database to multitenant structure."""
    db_path = os.environ.get('DATABASE_URL', 'sqlite:///rd_projects.db')

    # For SQLite
    if db_path.startswith('sqlite:///'):
        db_file = db_path.replace('sqlite:///', '')
        if not os.path.exists(db_file):
            print(f"Database file {db_file} not found. Creating new database.")
            return create_new_database()
        return migrate_sqlite(db_file)
    else:
        print("This script currently only supports SQLite databases.")
        print("For other databases, use Flask-Migrate or manual migration.")
        return False


def create_new_database():
    """Create new database with multitenant structure."""
    from app import create_app
    app = create_app()
    print("New database created with multitenant support.")
    return True


def migrate_sqlite(db_file):
    """Migrate SQLite database to multitenant structure."""
    print(f"Migrating database: {db_file}")

    # Backup database
    backup_file = f"{db_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    import shutil
    shutil.copy(db_file, backup_file)
    print(f"Backup created: {backup_file}")

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    try:
        # Check if tenants table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tenants'")
        if cursor.fetchone():
            print("Tenants table already exists. Migration may have been run before.")
        else:
            # Create tenants table
            print("Creating tenants table...")
            cursor.execute("""
                CREATE TABLE tenants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(200) NOT NULL,
                    slug VARCHAR(100) UNIQUE NOT NULL,
                    cnpj VARCHAR(20),
                    email VARCHAR(120),
                    phone VARCHAR(20),
                    address TEXT,
                    logo_url VARCHAR(500),
                    plan VARCHAR(50) DEFAULT 'basic',
                    max_users INTEGER DEFAULT 5,
                    max_projects INTEGER DEFAULT 10,
                    active BOOLEAN DEFAULT 1,
                    expires_at DATE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

        # Add tenant_id columns to existing tables
        tables_to_modify = [
            ('users', True),  # nullable for superadmin
            ('projects', False),
            ('expenses', False),
            ('resources', False),
            ('milestones', False),
            ('timesheets', False),
            ('public_calls', True),  # nullable for global calls
            ('project_calls', False)
        ]

        for table_name, nullable in tables_to_modify:
            try:
                # Check if column already exists
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]

                if 'tenant_id' not in columns:
                    print(f"Adding tenant_id to {table_name}...")
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN tenant_id INTEGER REFERENCES tenants(id)")
            except sqlite3.OperationalError as e:
                print(f"Warning: Could not modify {table_name}: {e}")

        # Create a default tenant if data exists
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        if user_count > 0:
            print("Creating default tenant for existing data...")

            # Check if default tenant exists
            cursor.execute("SELECT id FROM tenants WHERE slug = 'default'")
            tenant_row = cursor.fetchone()

            if tenant_row:
                default_tenant_id = tenant_row[0]
            else:
                cursor.execute("""
                    INSERT INTO tenants (name, slug, plan, max_users, max_projects, active)
                    VALUES ('Empresa Padrão', 'default', 'enterprise', 100, 1000, 1)
                """)
                default_tenant_id = cursor.lastrowid

            # Assign existing data to default tenant
            for table_name, nullable in tables_to_modify:
                if table_name == 'users':
                    # Keep superadmin without tenant
                    cursor.execute(f"""
                        UPDATE {table_name}
                        SET tenant_id = ?
                        WHERE tenant_id IS NULL AND role != 'superadmin'
                    """, (default_tenant_id,))
                elif nullable:
                    # Don't update nullable tables (public_calls are global)
                    pass
                else:
                    cursor.execute(f"""
                        UPDATE {table_name}
                        SET tenant_id = ?
                        WHERE tenant_id IS NULL
                    """, (default_tenant_id,))

            print(f"Assigned existing data to default tenant (ID: {default_tenant_id})")

        # Update unique constraints for projects (code unique per tenant)
        # SQLite doesn't support modifying constraints, so we skip this

        conn.commit()
        print("Migration completed successfully!")

        # Update superadmin user
        cursor.execute("SELECT id FROM users WHERE role = 'admin' AND username = 'admin'")
        admin = cursor.fetchone()
        if admin:
            cursor.execute("UPDATE users SET role = 'superadmin', tenant_id = NULL WHERE id = ?", (admin[0],))
            conn.commit()
            print("Converted admin user to superadmin")

        return True

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        print(f"Restoring from backup: {backup_file}")
        conn.close()
        import shutil
        shutil.copy(backup_file, db_file)
        return False

    finally:
        conn.close()


def verify_migration():
    """Verify the migration was successful."""
    from app import create_app
    from models import db, Tenant, User, Project

    app = create_app()
    with app.app_context():
        print("\n--- Migration Verification ---")
        print(f"Tenants: {Tenant.query.count()}")
        print(f"Users: {User.query.count()}")
        print(f"  - Superadmins: {User.query.filter_by(role='superadmin').count()}")
        print(f"Projects: {Project.query.count()}")

        # List tenants
        tenants = Tenant.query.all()
        for tenant in tenants:
            user_count = User.query.filter_by(tenant_id=tenant.id).count()
            project_count = Project.query.filter_by(tenant_id=tenant.id).count()
            print(f"\nTenant: {tenant.name} ({tenant.slug})")
            print(f"  Users: {user_count}/{tenant.max_users}")
            print(f"  Projects: {project_count}/{tenant.max_projects}")


if __name__ == '__main__':
    print("=" * 50)
    print("MIGRATION TO MULTITENANT STRUCTURE")
    print("=" * 50)

    success = migrate_database()

    if success:
        print("\n" + "=" * 50)
        verify_migration()
        print("\n" + "=" * 50)
        print("Migration completed!")
        print("\nDefault Super Admin credentials:")
        print("  Username: superadmin")
        print("  Password: super123")
        print("\nPlease change the password after first login.")
    else:
        print("Migration failed. Please check the errors above.")
