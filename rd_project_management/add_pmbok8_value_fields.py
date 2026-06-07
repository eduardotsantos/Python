#!/usr/bin/env python3
"""
Migration script to add PMBOK 8 Value Delivery fields to projects table.

Run this script to add:
- expected_value: Expected value in R$
- value_type: Type of value (ROI, Economia, Receita, Estratégico)
- value_status: Status of value capture (Não iniciado, Em captura, Parcial, Realizado)
- realized_value: Realized value in R$

Usage:
    python add_pmbok8_value_fields.py
"""

import sqlite3
import os

def migrate():
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'rd_management.db')

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(projects)")
    columns = [col[1] for col in cursor.fetchall()]

    migrations_done = []

    # Add expected_value column
    if 'expected_value' not in columns:
        cursor.execute("ALTER TABLE projects ADD COLUMN expected_value REAL DEFAULT 0.0")
        migrations_done.append('expected_value')
        print("Added column: expected_value")

    # Add value_type column
    if 'value_type' not in columns:
        cursor.execute("ALTER TABLE projects ADD COLUMN value_type VARCHAR(50)")
        migrations_done.append('value_type')
        print("Added column: value_type")

    # Add value_status column
    if 'value_status' not in columns:
        cursor.execute("ALTER TABLE projects ADD COLUMN value_status VARCHAR(50) DEFAULT 'Não iniciado'")
        migrations_done.append('value_status')
        print("Added column: value_status")

    # Add realized_value column
    if 'realized_value' not in columns:
        cursor.execute("ALTER TABLE projects ADD COLUMN realized_value REAL DEFAULT 0.0")
        migrations_done.append('realized_value')
        print("Added column: realized_value")

    conn.commit()
    conn.close()

    if migrations_done:
        print(f"\nMigration completed successfully!")
        print(f"Added {len(migrations_done)} new columns: {', '.join(migrations_done)}")
    else:
        print("No migrations needed - all columns already exist.")

    return True

if __name__ == '__main__':
    print("PMBOK 8 Value Delivery Migration")
    print("=" * 40)
    migrate()
