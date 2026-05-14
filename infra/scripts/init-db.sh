#!/bin/bash
set -e

echo "Initializing Palmi database extensions..."

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- UUID generation
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Trigram index for Chinese full-text search
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    
    -- Vector search (Phase 2 - install extension but don't create indexes yet)
    -- CREATE EXTENSION IF NOT EXISTS "vector";
    
    -- Verify extensions
    SELECT extname, extversion FROM pg_extension WHERE extname IN ('uuid-ossp', 'pg_trgm');
    
    RAISE NOTICE 'Palmi database initialized successfully!';
EOSQL

echo "Database initialization complete."
