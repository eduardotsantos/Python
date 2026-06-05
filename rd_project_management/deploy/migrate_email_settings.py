#!/usr/bin/env python3
"""
Migration Script - Email Settings for Tenant and User
Adds email configuration fields to Tenant and User models.

Uso:
    python3 migrate_email_settings.py
"""
import os
import sys

# Add project directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_migration():
    print("=" * 60)
    print("  MIGRATION - Email Settings (Tenant + User)")
    print("=" * 60)
    print()

    try:
        from app import create_app
        from models import db
        print("[OK] Modules imported")
    except ImportError as e:
        print(f"[ERROR] Import failed: {e}")
        sys.exit(1)

    app = create_app()

    with app.app_context():
        print()
        print("[1/2] Adding email fields to Tenant...")

        # Tenant email fields
        tenant_columns = [
            ("email_enabled", "BOOLEAN DEFAULT 0"),
            ("mail_server", "VARCHAR(200)"),
            ("mail_port", "INTEGER DEFAULT 587"),
            ("mail_use_tls", "BOOLEAN DEFAULT 1"),
            ("mail_use_ssl", "BOOLEAN DEFAULT 0"),
            ("mail_username", "VARCHAR(200)"),
            ("mail_password", "VARCHAR(200)"),
            ("mail_default_sender", "VARCHAR(200)")
        ]

        for col_name, col_type in tenant_columns:
            try:
                db.session.execute(db.text(f"ALTER TABLE tenants ADD COLUMN {col_name} {col_type}"))
                print(f"      + tenants.{col_name}")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"      - tenants.{col_name} (already exists)")
                else:
                    print(f"      ! tenants.{col_name}: {e}")

        print()
        print("[2/2] Adding email preference fields to User...")

        # User email preference fields
        user_columns = [
            ("email_notifications", "BOOLEAN DEFAULT 1"),
            ("email_briefing_daily", "BOOLEAN DEFAULT 1"),
            ("email_alerts", "BOOLEAN DEFAULT 1")
        ]

        for col_name, col_type in user_columns:
            try:
                db.session.execute(db.text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                print(f"      + users.{col_name}")
            except Exception as e:
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    print(f"      - users.{col_name} (already exists)")
                else:
                    print(f"      ! users.{col_name}: {e}")

        db.session.commit()

        print()
        print("=" * 60)
        print("  MIGRATION COMPLETED!")
        print("=" * 60)
        print()
        print("New Tenant fields:")
        print("  - email_enabled: Enable/disable email for tenant")
        print("  - mail_server: SMTP server address")
        print("  - mail_port: SMTP port (default 587)")
        print("  - mail_use_tls: Use TLS (default True)")
        print("  - mail_username: SMTP username")
        print("  - mail_password: SMTP password")
        print("  - mail_default_sender: Default sender email")
        print()
        print("New User fields:")
        print("  - email_notifications: Receive any notifications")
        print("  - email_briefing_daily: Receive daily briefing")
        print("  - email_alerts: Receive critical alerts")
        print()


if __name__ == '__main__':
    run_migration()
