import sys
import os

# Ensure the backend directory is in the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, create_tables
from app.models import User
from app.tool_functions import ingest_resume_folder
from app.config import settings

def main():
    print("=== 1. Initializing Database ===")
    print("Creating tables in Neon Database (if they don't exist)...")
    create_tables()
    
    db = SessionLocal()
    try:
        # 1. Create a dummy test user if we don't have one
        user = db.query(User).filter_by(email="test@hirex.com").first()
        if not user:
            user = User(name="Test Recruiter", email="test@hirex.com", role="RECRUITER")
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created dummy test user: {user.email} (ID: {user.id})")
        else:
            print(f"Found existing dummy test user: {user.email} (ID: {user.id})")
        
        # 2. Ingest all CVs from the configured folder
        print(f"\n=== 2. Scanning CV Folder ({settings.RESUME_DIR}) ===")
        print("Starting CV extraction and Groq JSON conversion...")
        print("NOTE: Previously ingested CVs will be automatically skipped based on file hash.")
        ingest_results = ingest_resume_folder(db)
        
        print("\n=== Ingestion Complete ===")
        print(f"  Total processed: {ingest_results.get('total')}")
        print(f"  Successful: {ingest_results.get('successful')}")
        print(f"  Skipped (Already in DB): {ingest_results.get('skipped')}")
        print(f"  Failed: {ingest_results.get('failed')}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
