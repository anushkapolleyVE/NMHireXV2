"""PostgreSQL engine and session setup."""
 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
 
from .config import settings
from .models import Base
 
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True
)
 
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)
 
 
def get_db():
    """Input: none. Output: SQLAlchemy session. Used by FastAPI routes."""
 
    db = SessionLocal()
 
    try:
        yield db
    finally:
        db.close()
 
 
def create_tables():
    Base.metadata.create_all(bind=engine)