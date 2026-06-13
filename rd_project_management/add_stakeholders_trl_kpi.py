"""
Migration script to add Stakeholders, TRL History, and Innovation KPI fields.
Run this script to update an existing database.
"""
import sqlite3
import os

def migrate_database(db_path='instance/rd_project.db'):
    """Add new tables and columns for stakeholders, TRL, and KPIs."""

    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add TRL and KPI fields to projects table
        project_columns = [
            ("trl", "INTEGER DEFAULT 1"),
            ("innovation_type", "VARCHAR(100)"),
            ("innovation_scope", "VARCHAR(100)"),
            ("target_market", "VARCHAR(200)"),
            ("competitive_advantage", "TEXT"),
            ("ip_strategy", "VARCHAR(100)"),
            ("time_to_market", "INTEGER"),
            ("expected_roi_percent", "FLOAT"),
            ("innovation_risk_level", "VARCHAR(50)")
        ]

        for col_name, col_type in project_columns:
            try:
                cursor.execute(f"ALTER TABLE projects ADD COLUMN {col_name} {col_type}")
                print(f"Added column projects.{col_name}")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e).lower():
                    print(f"Column projects.{col_name} already exists")
                else:
                    raise

        # Create project_stakeholders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_stakeholders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                name VARCHAR(200) NOT NULL,
                email VARCHAR(120),
                phone VARCHAR(20),
                organization VARCHAR(200),
                role VARCHAR(100) NOT NULL,
                influence_level VARCHAR(50) DEFAULT 'Médio',
                interest_level VARCHAR(50) DEFAULT 'Médio',
                engagement_strategy VARCHAR(100),
                receive_briefing BOOLEAN DEFAULT 0,
                receive_risk_alerts BOOLEAN DEFAULT 0,
                receive_financial_alerts BOOLEAN DEFAULT 0,
                receive_schedule_alerts BOOLEAN DEFAULT 0,
                receive_quality_alerts BOOLEAN DEFAULT 0,
                receive_compliance_alerts BOOLEAN DEFAULT 0,
                receive_status_reports BOOLEAN DEFAULT 0,
                active BOOLEAN DEFAULT 1,
                notes TEXT,
                created_by_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (created_by_id) REFERENCES users(id)
            )
        """)
        print("Created table project_stakeholders")

        # Create project_trl_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_trl_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                trl_from INTEGER,
                trl_to INTEGER NOT NULL,
                change_date DATE NOT NULL,
                justification TEXT,
                evidence TEXT,
                verified_by VARCHAR(200),
                changed_by_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tenant_id) REFERENCES tenants(id),
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (changed_by_id) REFERENCES users(id)
            )
        """)
        print("Created table project_trl_history")

        # Create indexes for better performance
        try:
            cursor.execute("CREATE INDEX idx_stakeholders_project ON project_stakeholders(project_id)")
            cursor.execute("CREATE INDEX idx_stakeholders_tenant ON project_stakeholders(tenant_id)")
            cursor.execute("CREATE INDEX idx_trl_history_project ON project_trl_history(project_id)")
            cursor.execute("CREATE INDEX idx_trl_history_tenant ON project_trl_history(tenant_id)")
            print("Created indexes")
        except sqlite3.OperationalError:
            print("Indexes already exist or could not be created")

        conn.commit()
        print("\nMigration completed successfully!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
        return False

    finally:
        conn.close()


if __name__ == '__main__':
    migrate_database()
