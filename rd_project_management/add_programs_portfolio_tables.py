#!/usr/bin/env python
"""Migration script to add programs, sync_schedules tables and program_id to projects."""

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
        print("ERRO: Banco de dados nao encontrado!")
        print("Uso: python add_programs_portfolio_tables.py [caminho_do_banco.db]")
        return False

    print(f"Usando banco de dados: {db_path}")

    if not os.path.exists(db_path):
        print(f"ERRO: Arquivo nao encontrado: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if programs table exists
        print("\n[1/4] Verificando tabela programs...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='programs'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE programs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id INTEGER NOT NULL,
                    code VARCHAR(50) NOT NULL,
                    name VARCHAR(300) NOT NULL,
                    description TEXT,
                    objective TEXT,
                    start_date DATE,
                    end_date DATE,
                    budget FLOAT DEFAULT 0.0,
                    status VARCHAR(50) DEFAULT 'Ativo',
                    manager_id INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                    FOREIGN KEY (manager_id) REFERENCES users(id),
                    UNIQUE (tenant_id, code)
                )
            ''')
            print("  - Tabela 'programs' criada")
        else:
            print("  - Tabela 'programs' ja existe")

        # Check if sync_schedules table exists
        print("\n[2/4] Verificando tabela sync_schedules...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_schedules'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE sync_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id INTEGER,
                    source VARCHAR(50) NOT NULL,
                    frequency VARCHAR(20) DEFAULT 'weekly',
                    day_of_week INTEGER DEFAULT 0,
                    hour INTEGER DEFAULT 8,
                    last_run DATETIME,
                    next_run DATETIME,
                    enabled BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id)
                )
            ''')
            print("  - Tabela 'sync_schedules' criada")
        else:
            print("  - Tabela 'sync_schedules' ja existe")

        # Check if program_id column exists in projects
        print("\n[3/4] Verificando coluna program_id em projects...")
        cursor.execute("PRAGMA table_info(projects)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'program_id' not in columns:
            cursor.execute("ALTER TABLE projects ADD COLUMN program_id INTEGER REFERENCES programs(id)")
            print("  - Coluna 'program_id' adicionada a tabela projects")
        else:
            print("  - Coluna 'program_id' ja existe")

        # Create indexes
        print("\n[4/4] Verificando indices...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_programs_tenant'")
        if not cursor.fetchone():
            cursor.execute("CREATE INDEX idx_programs_tenant ON programs(tenant_id)")
            print("  - Indice 'idx_programs_tenant' criado")
        else:
            print("  - Indice ja existe")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_projects_program'")
        if not cursor.fetchone():
            cursor.execute("CREATE INDEX idx_projects_program ON projects(program_id)")
            print("  - Indice 'idx_projects_program' criado")
        else:
            print("  - Indice ja existe")

        conn.commit()
        conn.close()

        print("\n" + "="*50)
        print("MIGRACAO CONCLUIDA COM SUCESSO!")
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
