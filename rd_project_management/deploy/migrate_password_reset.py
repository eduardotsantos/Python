"""
Migration: Add password reset token columns to users table.
Run this script once on the server after deploying (Linux or Windows).

Usage:
    python migrate_password_reset.py            (auto-detects the SQLite DB)
    python migrate_password_reset.py C:\\apps\\rd_project_managementv45\\rd_projects.db
    set DATABASE_PATH=... && python migrate_password_reset.py
"""
import sqlite3
import os
import sys
import glob

MIGRATIONS = [
    ("password_reset_token", "ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(100)"),
    ("password_reset_expires", "ALTER TABLE users ADD COLUMN password_reset_expires DATETIME"),
]


def find_databases():
    """Locate candidate SQLite databases (script may run from app root or deploy/)."""
    if len(sys.argv) > 1:
        return [sys.argv[1]]
    if os.environ.get('DATABASE_PATH'):
        return [os.environ['DATABASE_PATH']]

    here = os.path.dirname(os.path.abspath(__file__))
    app_root = os.path.dirname(here) if os.path.basename(here) == 'deploy' else here

    candidates = []
    for base in (app_root, os.getcwd()):
        candidates += glob.glob(os.path.join(base, '*.db'))
        candidates += glob.glob(os.path.join(base, 'instance', '*.db'))
    # Deduplicate preserving order
    seen = set()
    return [c for c in candidates if not (c in seen or seen.add(c))]


def migrate(db_path):
    print(f"\nBanco: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    for col_name, sql in MIGRATIONS:
        try:
            cur.execute(sql)
            conn.commit()
            print(f"  [OK] Coluna adicionada: {col_name}")
        except sqlite3.OperationalError as e:
            msg = str(e).lower()
            if "duplicate column" in msg:
                print(f"  [SKIP] Coluna ja existe: {col_name}")
            elif "no such table" in msg:
                print(f"  [SKIP] Tabela 'users' nao existe neste banco")
                break
            else:
                print(f"  [ERRO] {col_name}: {e}")

    conn.close()


if __name__ == '__main__':
    dbs = find_databases()
    if not dbs:
        print("[INFO] Nenhum banco SQLite encontrado.")
        print("       As colunas serao criadas automaticamente no primeiro start da aplicacao.")
        print("       Ou informe o caminho: python migrate_password_reset.py C:\\caminho\\banco.db")
    else:
        for db in dbs:
            migrate(db)
    print("\nMigracao concluida.")
