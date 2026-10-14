import os
import sys
from pathlib import Path
import traceback

# Ensure the backend root is in the Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

def print_header(title):
    print(f"\n{'='*50}\n{title}\n{'='*50}")

def print_result(step, success, error_msg=""):
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {step}")
    if not success and error_msg:
        print(f"       -> {error_msg}")

def run_diagnostics():
    print_header("NMHireX Backend Diagnostics")
    all_passed = True

    # 1. Structure Check
    expected_dirs = [
        "app/core", "app/api", "app/models", "app/services", 
        "scripts/db", "scripts/admin", "tests"
    ]
    expected_files = [
        "app/main.py", "app/core/config.py", "app/core/database.py", "app/core/auth.py",
        "app/api/routes.py", "app/models/schema.py", 
        "app/services/tool_functions.py", "app/services/skill_tree.py", "app/services/tools.py",
        ".env", "alembic.ini"
    ]

    print("\n--- Checking Directory Structure ---")
    for d in expected_dirs:
        exists = (BASE_DIR / d).is_dir()
        print_result(f"Directory: {d}", exists)
        if not exists: all_passed = False

    print("\n--- Checking Critical Files ---")
    for f in expected_files:
        exists = (BASE_DIR / f).is_file()
        print_result(f"File: {f}", exists)
        if not exists: all_passed = False

    if not all_passed:
        print("\n⚠️  Structure issues found. Please fix the missing files/folders before continuing.")
        return

    # 2. Imports Check
    print("\n--- Checking Internal Imports ---")
    try:
        from app.core.config import settings
        print_result("Imported app.core.config.settings", True)
        
        from app.models.schema import Base
        print_result("Imported app.models.schema.Base", True)
        
        from app.services.tool_functions import calculate_normal_score
        print_result("Imported app.services.tool_functions", True)
        
        from app.main import app
        print_result("Imported app.main.app (FastAPI instance)", True)
    except Exception as e:
        print_result("Internal Imports", False, f"{type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return

    # 3. Database Connection Check
    print("\n--- Checking Database Connection ---")
    try:
        from sqlalchemy import create_engine, text
        if not settings.DATABASE_URL:
            raise ValueError("DATABASE_URL is empty in .env")
        
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print_result("Database Connection Successful", True)
    except Exception as e:
        print_result("Database Connection", False, f"{type(e).__name__}: {str(e)}")
        all_passed = False

    # 4. API Health Check
    print("\n--- Checking API Endpoints ---")
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
        
        response = client.get("/health")
        if response.status_code == 200 and response.json() == {"status": "ok"}:
            print_result("GET /health Endpoint", True)
        else:
            print_result("GET /health Endpoint", False, f"Unexpected response: {response.status_code} - {response.text}")
            all_passed = False
            
    except Exception as e:
        print_result("API Health Check", False, str(e))
        all_passed = False

    # Final Verdict
    print_header("DIAGNOSTICS COMPLETE")
    if all_passed:
        print("🎉 ALL SYSTEMS GO! The new architecture is perfectly structured and operational.")
        print("You can now safely move to the enhancement phase.")
    else:
        print("⚠️ Errors detected. Please review the failed checks above.")

if __name__ == "__main__":
    run_diagnostics()