import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import SessionLocal
from app.models.schema import User
from app.core.auth import hash_password

def create_test_recruiter():
    db = SessionLocal()
    try:
        email = "test@hirex.com"
        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name="Test Recruiter",
                email=email,
                password_hash=hash_password("password123"),
                role="RECRUITER",
                status="APPROVED",
                is_active=True
            )
            db.add(user)
            db.commit()
            print(f"✅ Created test recruiter!\nEmail: {email}\nPassword: password123")
        else:
            user.status = "APPROVED"
            user.password_hash = hash_password("password123")
            db.commit()
            print(f"✅ Reset existing test recruiter!\nEmail: {email}\nPassword: password123")
    finally:
        db.close()

if __name__ == "__main__":
    create_test_recruiter()