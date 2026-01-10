-- Migration: Add S3 file tracking tables and BYOK support
-- Run this on your PostgreSQL database

-- 1. Add BYOK column to companies
ALTER TABLE companies ADD COLUMN IF NOT EXISTS kms_key_arn VARCHAR(255);

-- 2. Create activity_screenshots table
CREATE TABLE IF NOT EXISTS activity_screenshots (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    project_id INTEGER NOT NULL REFERENCES projects(id),
    activity_type VARCHAR(50) NOT NULL,
    session_id INTEGER NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_size_bytes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_activity_screenshots_session ON activity_screenshots(activity_type, session_id);
CREATE INDEX IF NOT EXISTS ix_activity_screenshots_company_project ON activity_screenshots(company_id, project_id);

-- 3. Create form_uploaded_files table
CREATE TABLE IF NOT EXISTS form_uploaded_files (
    id SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL REFERENCES companies(id),
    project_id INTEGER NOT NULL REFERENCES projects(id),
    form_page_route_id INTEGER NOT NULL REFERENCES form_page_routes(id),
    form_map_result_id INTEGER REFERENCES form_map_results(id),
    path_number INTEGER,
    s3_key VARCHAR(500) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    file_size_bytes INTEGER,
    field_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_form_uploaded_files_route ON form_uploaded_files(form_page_route_id);
CREATE INDEX IF NOT EXISTS ix_form_uploaded_files_company ON form_uploaded_files(company_id);