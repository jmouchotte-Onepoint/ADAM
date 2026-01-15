-- 1. Creation d'une table pour des apps multitenant
CREATE TABLE IF NOT EXISTS adam.tenants (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    creation_date TIMESTAMP DEFAULT NOW()
);

-- 2. Association PG Rol In table
CREATE TABLE IF NOT EXISTS adam.tenants_per_users (
    tenant_id VARCHAR(36) NOT NULL REFERENCES adam.tenants(id),
    pg_user VARCHAR(100) NOT NULL,
    creation_date TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (tenant_id,pg_user)
);