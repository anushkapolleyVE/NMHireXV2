import sys
import logging
from sqlalchemy import create_engine, text
from app.config import settings

logging.basicConfig(level=logging.INFO)

indexes = [
    "CREATE INDEX IF NOT EXISTS ix_job_req_mandatory_skills ON job_requirements USING gin (mandatory_skills);",
    "CREATE INDEX IF NOT EXISTS ix_job_req_preferred_skills ON job_requirements USING gin (preferred_skills);",
    "CREATE INDEX IF NOT EXISTS ix_job_req_education ON job_requirements USING gin (education);",
    "CREATE INDEX IF NOT EXISTS ix_job_req_domains ON job_requirements USING gin (domains);",
    "CREATE INDEX IF NOT EXISTS ix_candidate_normalized_profile ON candidates USING gin (normalized_profile);",
    "CREATE INDEX IF NOT EXISTS ix_resume_parsed_data ON resumes USING gin (parsed_data);",
    "CREATE INDEX IF NOT EXISTS ix_candidate_project_technologies ON candidate_projects USING gin (technologies);"
]

def apply_indexes():
    print("Connecting to database...")
    engine = create_engine(settings.DATABASE_URL)
    # Using raw connection to execute DDL safely
    with engine.connect() as conn:
        for idx in indexes:
            print(f"Applying: {idx}")
            conn.execute(text(idx))
        conn.commit()
    print("All GIN indexes applied successfully!")

if __name__ == "__main__":
    apply_indexes()
