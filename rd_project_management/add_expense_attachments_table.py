#!/usr/bin/env python
"""Migration script to add expense_attachments table to existing databases."""

import sqlite3
import os
import sys
import glob

def find_database():
    """Find the SQLite database file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Common database locations
    possible_paths = [
        os.path.join(script_dir, 'instance', 'rd_project.db'),
        os.path.join(script_dir, 'instance', 'rd_projects.db'),
        os.path.join(script_dir, 'rd_project.db'),
        os.path.join(script_dir, 'rd_projects.db'),
        os.path.join(script_dir, 'database.db'),
        os.path.join(script_dir, 'app.db'),
    ]

    # Check explicit paths
    for path in possible_paths:
        if os.path.exists(path):
            return path

    # Search for any .db file in instance folder
    instance_dbs = glob.glob(os.path.join(script_dir, 'instance', '*.db'))
    if instance_dbs:
        return instance_dbs[0]

    # Search for any .db file in current folder
    current_dbs = glob.glob(os.path.join(script_dir, '*.db'))
    if current_dbs:
        return current_dbs[0]

    return None


def migrate(db_path=None):
    """Run the migration."""
    if db_path is None:
        db_path = find_database()

    if db_path is None:
        print("ERRO: Banco de dados não encontrado!")
        print("Uso: python add_expense_attachments_table.py [caminho_do_banco.db]")
        print("\nExemplo:")
        print("  python add_expense_attachments_table.py instance/rd_projects.db")
        return False

    print(f"Usando banco de dados: {db_path}")

    if not os.path.exists(db_path):
        print(f"ERRO: Arquivo não encontrado: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='expense_attachments'")
        if cursor.fetchone():
            print("Tabela 'expense_attachments' já existe. Nenhuma ação necessária.")
            conn.close()
            return True

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
        print("SUCESSO! Tabela 'expense_attachments' criada com sucesso!")
        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"ERRO SQLite: {e}")
        return False
    except Exception as e:
        print(f"ERRO: {e}")
        return False


if __name__ == '__main__':
    # Accept database path as command line argument
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    success = migrate(db_path)
    sys.exit(0 if success else 1)
