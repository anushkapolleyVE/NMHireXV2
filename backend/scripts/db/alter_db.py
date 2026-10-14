import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import engine
from sqlalchemy import text

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN status VARCHAR(30) DEFAULT 'PENDING' NOT NULL;"))
    print("Successfully added status column.")
except Exception as e:
    print(f"Error or column already exists: {e}")