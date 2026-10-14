from app.database import engine
from app.models import Base

print("Creating database tables...")

Base.metadata.create_all(bind=engine)

print("All tables created successfully.")