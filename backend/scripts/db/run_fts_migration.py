"""Run FTS migration: add search_vector column to resumes table."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine, text
from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not found in environment")
    sys.exit(1)

engine = create_engine(DATABASE_URL)

sql_add_column = """
ALTER TABLE resumes
ADD COLUMN IF NOT EXISTS search_vector tsvector
GENERATED ALWAYS AS (
    to_tsvector('english', coalesce(raw_text, ''))
) STORED;
"""

sql_add_index = """
CREATE INDEX IF NOT EXISTS idx_resumes_search_vector
ON resumes USING GIN(search_vector);
"""

sql_verify = "SELECT COUNT(*) FROM resumes WHERE search_vector IS NOT NULL;"

with engine.connect() as conn:
    print("Adding search_vector column...")
    conn.execute(text(sql_add_column))
    conn.commit()
    print("Column added.")

    print("Creating GIN index...")
    conn.execute(text(sql_add_index))
    conn.commit()
    print("Index created.")

    result = conn.execute(text(sql_verify))
    count = result.scalar()
    print(f"Migration complete. Resumes with search_vector populated: {count}")