-- =============================================================================
-- PostgreSQL Initialization Script - System B+R
-- =============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- =============================================================================
-- Event Store Schema
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS event_store;

-- Event store table
CREATE TABLE IF NOT EXISTS event_store.events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(255) NOT NULL,
    event_type VARCHAR(255) NOT NULL,
    event_data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    version INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_aggregate_version UNIQUE (aggregate_id, version)
);

CREATE INDEX idx_events_aggregate_id ON event_store.events(aggregate_id);
CREATE INDEX idx_events_aggregate_type ON event_store.events(aggregate_type);
CREATE INDEX idx_events_event_type ON event_store.events(event_type);
CREATE INDEX idx_events_created_at ON event_store.events(created_at);
CREATE INDEX idx_events_data ON event_store.events USING GIN (event_data);

-- Snapshots table
CREATE TABLE IF NOT EXISTS event_store.snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(255) NOT NULL,
    state JSONB NOT NULL,
    version INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_snapshot_version UNIQUE (aggregate_id)
);

CREATE INDEX idx_snapshots_aggregate_id ON event_store.snapshots(aggregate_id);

-- =============================================================================
-- Read Models Schema
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS read_models;

-- Projects (B+R projects)
CREATE TABLE IF NOT EXISTS read_models.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    start_date DATE,
    end_date DATE,
    fiscal_year INTEGER NOT NULL,
    total_expenses DECIMAL(15, 2) DEFAULT 0,
    br_qualified_expenses DECIMAL(15, 2) DEFAULT 0,
    ip_qualified_expenses DECIMAL(15, 2) DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_projects_fiscal_year ON read_models.projects(fiscal_year);
CREATE INDEX idx_projects_status ON read_models.projects(status);
CREATE INDEX idx_projects_name ON read_models.projects USING GIN (name gin_trgm_ops);

-- Documents
CREATE TABLE IF NOT EXISTS read_models.documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES read_models.projects(id),
    document_type VARCHAR(100) NOT NULL,  -- invoice, receipt, contract, etc.
    filename VARCHAR(500) NOT NULL,
    original_path VARCHAR(1000),
    processed_path VARCHAR(1000),
    file_size INTEGER,
    mime_type VARCHAR(100),
    ocr_status VARCHAR(50) DEFAULT 'pending',  -- pending, processing, completed, failed
    ocr_confidence DECIMAL(5, 4),
    ocr_text TEXT,
    extracted_data JSONB DEFAULT '{}',
    validation_status VARCHAR(50) DEFAULT 'pending',
    validation_errors JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_documents_project_id ON read_models.documents(project_id);
CREATE INDEX idx_documents_type ON read_models.documents(document_type);
CREATE INDEX idx_documents_ocr_status ON read_models.documents(ocr_status);
CREATE INDEX idx_documents_ocr_text ON read_models.documents USING GIN (to_tsvector('polish', ocr_text));

-- Expenses (wydatki)
CREATE TABLE IF NOT EXISTS read_models.expenses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES read_models.projects(id),
    document_id UUID REFERENCES read_models.documents(id),
    
    -- Dane z faktury
    invoice_number VARCHAR(100),
    invoice_date DATE,
    vendor_name VARCHAR(500),
    vendor_nip VARCHAR(20),
    
    -- Kwoty
    net_amount DECIMAL(15, 2) NOT NULL,
    vat_amount DECIMAL(15, 2) DEFAULT 0,
    gross_amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'PLN',
    
    -- Klasyfikacja B+R
    expense_category VARCHAR(100),  -- personnel, materials, equipment, services, etc.
    br_category VARCHAR(100),  -- zgodnie z art. 26e
    br_qualified BOOLEAN DEFAULT FALSE,
    br_qualification_reason TEXT,
    br_deduction_rate DECIMAL(5, 2) DEFAULT 1.00,  -- 1.00 = 100%, 2.00 = 200%
    
    -- Klasyfikacja IP Box
    ip_qualified BOOLEAN DEFAULT FALSE,
    ip_category VARCHAR(100),
    nexus_category VARCHAR(1),  -- a, b, c, d
    
    -- LLM klasyfikacja
    llm_classification JSONB DEFAULT '{}',
    llm_confidence DECIMAL(5, 4),
    manual_override BOOLEAN DEFAULT FALSE,
    
    -- Status
    status VARCHAR(50) DEFAULT 'draft',
    needs_clarification BOOLEAN DEFAULT FALSE,
    clarification_questions JSONB DEFAULT '[]',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_expenses_project_id ON read_models.expenses(project_id);
CREATE INDEX idx_expenses_document_id ON read_models.expenses(document_id);
CREATE INDEX idx_expenses_invoice_date ON read_models.expenses(invoice_date);
CREATE INDEX idx_expenses_vendor_nip ON read_models.expenses(vendor_nip);
CREATE INDEX idx_expenses_br_qualified ON read_models.expenses(br_qualified);
CREATE INDEX idx_expenses_ip_qualified ON read_models.expenses(ip_qualified);
CREATE INDEX idx_expenses_status ON read_models.expenses(status);

-- Revenues (przychody)
CREATE TABLE IF NOT EXISTS read_models.revenues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES read_models.projects(id),
    document_id UUID REFERENCES read_models.documents(id),
    
    -- Dane z faktury
    invoice_number VARCHAR(100),
    invoice_date DATE,
    client_name VARCHAR(500),
    client_nip VARCHAR(20),
    
    -- Kwoty
    net_amount DECIMAL(15, 2) NOT NULL,
    vat_amount DECIMAL(15, 2) DEFAULT 0,
    gross_amount DECIMAL(15, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'PLN',
    
    -- Klasyfikacja IP Box
    ip_qualified BOOLEAN DEFAULT FALSE,
    ip_type VARCHAR(100),  -- typ kwalifikowanego IP
    ip_description TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'draft',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_revenues_project_id ON read_models.revenues(project_id);
CREATE INDEX idx_revenues_invoice_date ON read_models.revenues(invoice_date);
CREATE INDEX idx_revenues_ip_qualified ON read_models.revenues(ip_qualified);

-- Monthly Reports
CREATE TABLE IF NOT EXISTS read_models.monthly_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES read_models.projects(id),
    fiscal_year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month >= 1 AND month <= 12),
    
    -- Podsumowanie wydatków
    total_expenses DECIMAL(15, 2) DEFAULT 0,
    br_expenses DECIMAL(15, 2) DEFAULT 0,
    br_deduction DECIMAL(15, 2) DEFAULT 0,
    ip_expenses DECIMAL(15, 2) DEFAULT 0,
    
    -- Podsumowanie przychodów
    total_revenues DECIMAL(15, 2) DEFAULT 0,
    ip_revenues DECIMAL(15, 2) DEFAULT 0,
    
    -- Liczniki dokumentów
    documents_count INTEGER DEFAULT 0,
    pending_documents INTEGER DEFAULT 0,
    needs_clarification INTEGER DEFAULT 0,
    
    -- Status raportu
    status VARCHAR(50) DEFAULT 'draft',
    generated_at TIMESTAMP WITH TIME ZONE,
    report_data JSONB DEFAULT '{}',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_monthly_report UNIQUE (project_id, fiscal_year, month)
);

CREATE INDEX idx_monthly_reports_project ON read_models.monthly_reports(project_id);
CREATE INDEX idx_monthly_reports_period ON read_models.monthly_reports(fiscal_year, month);

-- Clarifications (wyjaśnienia)
CREATE TABLE IF NOT EXISTS read_models.clarifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    expense_id UUID REFERENCES read_models.expenses(id),
    
    question TEXT NOT NULL,
    question_type VARCHAR(100),  -- br_purpose, br_innovation, expense_category, etc.
    answer TEXT,
    answered_at TIMESTAMP WITH TIME ZONE,
    
    auto_generated BOOLEAN DEFAULT TRUE,
    llm_suggested_answer TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_clarifications_expense ON read_models.clarifications(expense_id);
CREATE INDEX idx_clarifications_unanswered ON read_models.clarifications(expense_id) WHERE answer IS NULL;

-- =============================================================================
-- Users & Auth Schema
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON auth.users(email);

-- Sessions
CREATE TABLE IF NOT EXISTS auth.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON auth.sessions(user_id);
CREATE INDEX idx_sessions_expires ON auth.sessions(expires_at);

-- =============================================================================
-- LiteLLM Schema (for spend tracking)
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS litellm;

CREATE TABLE IF NOT EXISTS litellm.spend_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    request_id VARCHAR(255),
    model VARCHAR(255),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost DECIMAL(15, 6),
    user_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_spend_logs_model ON litellm.spend_logs(model);
CREATE INDEX idx_spend_logs_created ON litellm.spend_logs(created_at);

-- =============================================================================
-- Functions & Triggers
-- =============================================================================

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update triggers
CREATE TRIGGER update_projects_timestamp
    BEFORE UPDATE ON read_models.projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_documents_timestamp
    BEFORE UPDATE ON read_models.documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_expenses_timestamp
    BEFORE UPDATE ON read_models.expenses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_revenues_timestamp
    BEFORE UPDATE ON read_models.revenues
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- =============================================================================
-- Initial Data
-- =============================================================================

-- Insert default project
INSERT INTO read_models.projects (id, name, description, fiscal_year, status)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'Prototypowy system modularny',
    'Projekt B+R: Prototypowy system modularny dla firmy Tomasz Sapletta (NIP: 5881918662). Obejmuje rozwój nowych technologii, testowanie prototypów i dokumentację innowacyjnych rozwiązań.',
    2025,
    'active'
) ON CONFLICT DO NOTHING;

-- Insert default admin user (password: admin123 - change in production!)
INSERT INTO auth.users (email, password_hash, full_name, role)
VALUES (
    'admin@prototypowy.pl',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.SQ/pjrklvqX.Ki',  -- bcrypt hash of 'admin123'
    'Administrator',
    'admin'
) ON CONFLICT DO NOTHING;

-- Grant permissions
GRANT USAGE ON SCHEMA event_store TO br_admin;
GRANT USAGE ON SCHEMA read_models TO br_admin;
GRANT USAGE ON SCHEMA auth TO br_admin;
GRANT USAGE ON SCHEMA litellm TO br_admin;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA event_store TO br_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA read_models TO br_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth TO br_admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA litellm TO br_admin;

GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA event_store TO br_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA read_models TO br_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA auth TO br_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA litellm TO br_admin;
