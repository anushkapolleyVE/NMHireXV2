import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import SessionLocal
from app.models.schema import User
from app.core.auth import hash_password

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