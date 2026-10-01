#!/usr/bin/env python
"""Migration script to add meeting_minutes table."""

import sqlite3
import os
import sys
import glob


def find_database():
    """Find the SQLite database file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))

    possible_paths = [
        os.path.join(script_dir, 'instance', 'rd_project.db'),
        os.path.join(script_dir, 'instance', 'rd_projects.db'),
        os.path.join(script_dir, 'rd_project.db'),
        os.path.join(script_dir, 'rd_projects.db'),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    instance_dbs = glob.glob(os.path.join(script_dir, 'instance', '*.db'))
    if instance_dbs:
        return instance_dbs[0]

    return None


def migrate(db_path=None):
    """Run the migration."""
    if db_path is None:
        db_path = find_database()

    if db_path is None:
        print("ERRO: Banco de dados não encontrado!")
        print("Uso: python add_meeting_minutes_table.py [caminho_do_banco.db]")
        return False

    print(f"Usando banco de dados: {db_path}")

    if not os.path.exists(db_path):
        print(f"ERRO: Arquivo não encontrado: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if meeting_minutes table exists
        print("\n[1/2] Verificando tabela meeting_minutes...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='meeting_minutes'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE meeting_minutes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    title VARCHAR(300) NOT NULL,
                    meeting_date DATE NOT NULL,
                    meeting_time VARCHAR(10),
                    location VARCHAR(200),
                    participants TEXT,
                    transcription TEXT,
                    generated_minutes TEXT,
                    status VARCHAR(50) DEFAULT 'Rascunho',
                    attachment_filename VARCHAR(255),
                    attachment_stored VARCHAR(255),
                    created_by_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (created_by_id) REFERENCES users(id)
                )
            ''')
            print("  - Tabela 'meeting_minutes' criada")
        else:
            print("  - Tabela 'meeting_minutes' já existe")

        # Create index
        print("\n[2/2] Verificando índices...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_meeting_minutes_project'")
        if not cursor.fetchone():
            cursor.execute("CREATE INDEX idx_meeting_minutes_project ON meeting_minutes(project_id, meeting_date)")
            print("  - Índice 'idx_meeting_minutes_project' criado")
        else:
            print("  - Índice já existe")

        conn.commit()
        conn.close()

        print("\n" + "="*50)
        print("MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        print("="*50)
        return True

    except sqlite3.Error as e:
        print(f"ERRO SQLite: {e}")
        return False
    except Exception as e:
        print(f"ERRO: {e}")
        return False


if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    success = migrate(db_path)
    sys.exit(0 if success else 1)
