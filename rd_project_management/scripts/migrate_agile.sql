-- Migration script for Agile module
-- Run this SQL to add Sprint table and new Milestone columns

-- Create sprints table
CREATE TABLE IF NOT EXISTS sprints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    number INTEGER DEFAULT 1,
    goal TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'Planejado',
    velocity INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Add new columns to milestones table
-- Note: SQLite doesn't support IF NOT EXISTS for columns, so these may fail if already exist
ALTER TABLE milestones ADD COLUMN sprint_id INTEGER REFERENCES sprints(id);
ALTER TABLE milestones ADD COLUMN responsible_id INTEGER REFERENCES users(id);
ALTER TABLE milestones ADD COLUMN priority VARCHAR(20) DEFAULT 'Média';
ALTER TABLE milestones ADD COLUMN story_points INTEGER DEFAULT 0;
