"""
Migration: Add password reset token columns to users table.
Run this script once on the server after deploying.
"""
import sqlite3
import os

DB_PATH = os.environ.get('DATABASE_PATH', '../pd_management.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    migrations = [
        ("password_reset_token", "ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(100)"),
        ("password_reset_expires", "ALTER TABLE users ADD COLUMN password_reset_expires DATETIME"),
    ]

    for col_name, sql in migrations:
        try:
            cur.execute(sql)
            conn.commit()
            print(f"[OK] Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"[SKIP] Column already exists: {col_name}")
            else:
                print(f"[ERROR] {col_name}: {e}")

    conn.close()
    print("Migration complete.")

if __name__ == '__main__':
    migrate()
