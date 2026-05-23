#!/usr/bin/env python
"""Migration script to add audit_logs table and new tenant/user fields."""

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
        print("Uso: python add_audit_and_tenant_fields.py [caminho_do_banco.db]")
        return False

    print(f"Usando banco de dados: {db_path}")

    if not os.path.exists(db_path):
        print(f"ERRO: Arquivo nao encontrado: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. Add state and municipality to tenants table
        print("\n[1/3] Verificando campos state e municipality na tabela tenants...")
        cursor.execute("PRAGMA table_info(tenants)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'state' not in columns:
            cursor.execute("ALTER TABLE tenants ADD COLUMN state VARCHAR(2)")
            print("  - Campo 'state' adicionado")
        else:
            print("  - Campo 'state' ja existe")

        if 'municipality' not in columns:
            cursor.execute("ALTER TABLE tenants ADD COLUMN municipality VARCHAR(200)")
            print("  - Campo 'municipality' adicionado")
        else:
            print("  - Campo 'municipality' ja existe")

        # 2. Check if audit_logs table exists
        print("\n[2/3] Verificando tabela audit_logs...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
        if not cursor.fetchone():
            cursor.execute('''
                CREATE TABLE audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_id INTEGER,
                    user_id INTEGER,
                    action VARCHAR(50) NOT NULL,
                    entity_type VARCHAR(100),
                    entity_id INTEGER,
                    entity_name VARCHAR(300),
                    details TEXT,
                    ip_address VARCHAR(50),
                    user_agent VARCHAR(500),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            print("  - Tabela 'audit_logs' criada")
        else:
            print("  - Tabela 'audit_logs' ja existe")

        # 3. Create index for audit_logs
        print("\n[3/3] Verificando indices...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_audit_logs_tenant_date'")
        if not cursor.fetchone():
            cursor.execute("CREATE INDEX idx_audit_logs_tenant_date ON audit_logs(tenant_id, created_at)")
            print("  - Indice 'idx_audit_logs_tenant_date' criado")
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
