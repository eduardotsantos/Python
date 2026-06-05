#!/usr/bin/env python3
"""
Migration Script - Email Settings for Tenant and User
Adds email configuration fields directly to SQLite database.

Uso:
    python3 migrate_email_settings.py
"""
import os
import sys
import sqlite3

def run_migration():
    print("=" * 60)
    print("  MIGRATION - Email Settings (Tenant + User)")
    print("=" * 60)
    print()

    # Find database file
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rd_projects.db')

    if not os.path.exists(db_path):
        # Try alternative paths
        alt_paths = [
            'rd_projects.db',
            '../rd_projects.db',
            'instance/rd_projects.db'
        ]
        for alt in alt_paths:
            full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), alt)
            if os.path.exists(full_path):
                db_path = full_path
                break

    print(f"[INFO] Database: {db_path}")

    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at {db_path}")
        print("        Please specify the correct path.")
        sys.exit(1)

    # Connect directly to SQLite
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print()
    print("[1/2] Adding email fields to tenants table...")

    tenant_columns = [
        ("email_enabled", "INTEGER DEFAULT 0"),
        ("mail_server", "VARCHAR(200)"),
        ("mail_port", "INTEGER DEFAULT 587"),
        ("mail_use_tls", "INTEGER DEFAULT 1"),
        ("mail_use_ssl", "INTEGER DEFAULT 0"),
        ("mail_username", "VARCHAR(200)"),
        ("mail_password", "VARCHAR(200)"),
        ("mail_default_sender", "VARCHAR(200)")
    ]

    for col_name, col_type in tenant_columns:
        try:
            cursor.execute(f"ALTER TABLE tenants ADD COLUMN {col_name} {col_type}")
            print(f"      + tenants.{col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"      - tenants.{col_name} (already exists)")
            else:
                print(f"      ! tenants.{col_name}: {e}")

    print()
    print("[2/2] Adding email preference fields to users table...")

    user_columns = [
        ("email_notifications", "INTEGER DEFAULT 1"),
        ("email_briefing_daily", "INTEGER DEFAULT 1"),
        ("email_alerts", "INTEGER DEFAULT 1")
    ]

    for col_name, col_type in user_columns:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"      + users.{col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"      - users.{col_name} (already exists)")
            else:
                print(f"      ! users.{col_name}: {e}")

    conn.commit()
    conn.close()

    print()
    print("=" * 60)
    print("  MIGRATION COMPLETED!")
    print("=" * 60)
    print()
    print("New Tenant fields:")
    print("  - email_enabled: Enable/disable email for tenant (0/1)")
    print("  - mail_server: SMTP server address")
    print("  - mail_port: SMTP port (default 587)")
    print("  - mail_use_tls: Use TLS (default 1)")
    print("  - mail_username: SMTP username")
    print("  - mail_password: SMTP password")
    print("  - mail_default_sender: Default sender email")
    print()
    print("New User fields:")
    print("  - email_notifications: Receive any notifications (0/1)")
    print("  - email_briefing_daily: Receive daily briefing (0/1)")
    print("  - email_alerts: Receive critical alerts (0/1)")
    print()
    print("To enable email for a tenant, run:")
    print("  UPDATE tenants SET email_enabled=1, mail_server='smtp.gmail.com',")
    print("    mail_username='your@email.com', mail_password='app-password'")
    print("  WHERE id=1;")
    print()


if __name__ == '__main__':
    run_migration()
