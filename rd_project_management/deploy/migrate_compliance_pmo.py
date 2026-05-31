#!/usr/bin/env python3
"""
Migration Script - Compliance Module Tables
Cria as tabelas para: Risk, PendingItem, NonConformity, Bug, CorrectiveAction

Uso:
    python3 migrate_compliance_pmo.py

Este script é idempotente - pode ser executado múltiplas vezes sem problemas.
"""
import os
import sys

# Adicionar diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_migration():
    print("=" * 60)
    print("  MIGRATION - Central de Conformidade + PMO IA")
    print("=" * 60)
    print()

    # Importar app e db
    try:
        from app import create_app
        from models import db, Risk, PendingItem, NonConformity, Bug, CorrectiveAction
        print("[OK] Módulos importados com sucesso")
    except ImportError as e:
        print(f"[ERRO] Falha ao importar: {e}")
        print("       Verifique se está no diretório correto do projeto.")
        sys.exit(1)

    # Criar app context
    app = create_app()

    with app.app_context():
        print()
        print("[1/3] Verificando conexão com banco de dados...")

        try:
            # Testar conexão
            db.engine.connect()
            print("      Conexão OK")
        except Exception as e:
            print(f"[ERRO] Falha na conexão: {e}")
            sys.exit(1)

        print()
        print("[2/3] Criando tabelas (se não existirem)...")

        # Listar tabelas a serem criadas
        tables_to_create = [
            ('risks', Risk),
            ('pending_items', PendingItem),
            ('non_conformities', NonConformity),
            ('bugs', Bug),
            ('corrective_actions', CorrectiveAction)
        ]

        for table_name, model in tables_to_create:
            try:
                if not db.engine.dialect.has_table(db.engine.connect(), table_name):
                    model.__table__.create(db.engine)
                    print(f"      ✓ Tabela '{table_name}' criada")
                else:
                    print(f"      - Tabela '{table_name}' já existe")
            except Exception as e:
                print(f"      ✗ Erro ao criar '{table_name}': {e}")

        print()
        print("[3/3] Verificando estrutura das tabelas...")

        # Verificar se as tabelas têm as colunas esperadas
        from sqlalchemy import inspect
        inspector = inspect(db.engine)

        for table_name, model in tables_to_create:
            try:
                columns = [c['name'] for c in inspector.get_columns(table_name)]
                print(f"      ✓ {table_name}: {len(columns)} colunas")
            except Exception as e:
                print(f"      ✗ {table_name}: {e}")

        print()
        print("=" * 60)
        print("  MIGRATION CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        print()
        print("Novas tabelas disponíveis:")
        print("  - risks: Registro de riscos do projeto")
        print("  - pending_items: Pendências com prazos")
        print("  - non_conformities: Não conformidades (NC)")
        print("  - bugs: Rastreamento de bugs")
        print("  - corrective_actions: Ações corretivas vinculadas")
        print()


if __name__ == '__main__':
    run_migration()
