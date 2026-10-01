import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine
from sqlalchemy import text

try:
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN status VARCHAR(30) DEFAULT 'PENDING' NOT NULL;"))
    print("Successfully added status column.")
except Exception as e:
    print(f"Error or column already exists: {e}")
