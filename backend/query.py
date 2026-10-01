import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User

db = SessionLocal()
users = db.query(User).all()
for u in users:
    print(f"Name: {u.name}, Email: {u.email}, Role: {u.role}, Status: {getattr(u, 'status', 'N/A')}")
