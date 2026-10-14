from uuid import UUID

from app.database import SessionLocal
from app.models import Candidate


db = SessionLocal()

try:
    candidate = db.get(
        Candidate,
        UUID("c16a31d1-95cf-49f0-8596-4cda766a7440")
    )

    if candidate:
        print("\nCandidate:")
        print(candidate.name)

        print("\nNormalized Profile:")
        print(candidate.normalized_profile)
    else:
        print("Candidate not found.")

finally:
    db.close()