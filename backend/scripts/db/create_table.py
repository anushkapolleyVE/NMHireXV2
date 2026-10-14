import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.database import engine
from app.models.schema import Base

print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("All tables created successfully.")