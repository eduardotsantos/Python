"""
Migration script to add language preference to User model.
Run this script to update an existing database.
"""
import sqlite3
import os

def migrate_database(db_path='instance/rd_project.db'):
    """Add language column to users table."""

    if not os.path.exists(db_path):
        # Try alternative paths
        alt_paths = ['rd_projects.db', 'instance/rd_projects.db']
        for alt in alt_paths:
            if os.path.exists(alt):
                db_path = alt
                break
        else:
            print(f"Database not found. Tried: {db_path}, {alt_paths}")
            return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'language' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN language VARCHAR(10) DEFAULT 'pt_BR'")
            print("Added 'language' column to users table")
        else:
            print("'language' column already exists")

        conn.commit()
        print("Migration completed successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        return False

    finally:
        conn.close()


if __name__ == '__main__':
    migrate_database()
