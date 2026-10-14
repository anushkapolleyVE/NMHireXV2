import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import User
from app.auth import hash_password

def seed_admin():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@hirex.com").first()
        
        if not admin:
            print("Creating admin user...")
            admin = User(
                name="Admin User",
                email="admin@hirex.com",
                password_hash=hash_password("admin123"),
                role="ADMIN",
                is_active=True
            )
            db.add(admin)
            db.commit()
            print("Admin user created successfully!")
            print("Admin Email/UserID: admin@hirex.com")
            print("Password: admin123")
        else:
            print("Admin user already exists.")
            print("Admin Email/UserID: admin@hirex.com")
            
    finally:
        db.close()

if __name__ == "__main__":
    seed_admin()
