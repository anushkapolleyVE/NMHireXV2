-- =============================================================
-- Migration: Add FTS search_vector to resumes table
-- Run once against your PostgreSQL database.
-- =============================================================

-- Step 1: Add the generated tsvector column.
-- This is automatically kept in sync by PostgreSQL whenever
-- raw_text is inserted or updated. No application code needed.
ALTER TABLE resumes
ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
    to_tsvector(
        'english',
        coalesce(raw_text, '')
    )
) STORED;

-- Step 2: Create GIN index for fast FTS lookups.
CREATE INDEX IF NOT EXISTS idx_resumes_search_vector
ON resumes
USING GIN(search_vector);

-- Verify
SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'resumes'
  AND column_name = 'search_vector';
