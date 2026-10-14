import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import SessionLocal
from app.models.schema import User

db = SessionLocal()
users = db.query(User).all()
for u in users:
    print(f"Name: {u.name}, Email: {u.email}, Role: {u.role}, Status: {getattr(u, 'status', 'N/A')}")