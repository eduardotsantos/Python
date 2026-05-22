#!/usr/bin/env python
"""Migration script to add expense_attachments table to existing databases."""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'rd_project.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        print("Run the application first to create the database.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='expense_attachments'")
    if cursor.fetchone():
        print("Table 'expense_attachments' already exists.")
        conn.close()
        return

    # Create the table
    cursor.execute('''
        CREATE TABLE expense_attachments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            expense_id INTEGER NOT NULL,
            filename VARCHAR(255) NOT NULL,
            stored_filename VARCHAR(255) NOT NULL,
            file_type VARCHAR(50) NOT NULL,
            file_size INTEGER,
            attachment_type VARCHAR(50) NOT NULL,
            uploaded_by_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id),
            FOREIGN KEY (expense_id) REFERENCES expenses(id),
            FOREIGN KEY (uploaded_by_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    print("Table 'expense_attachments' created successfully!")
    conn.close()

if __name__ == '__main__':
    migrate()
