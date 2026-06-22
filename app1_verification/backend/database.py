import os
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app1.db")


# SQLite needs check_same_thread=False; PostgreSQL ignores connect_args
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_importjob_columns():
    if not DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "import_jobs" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("import_jobs")}
    if "uploaded_by" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE import_jobs ADD COLUMN uploaded_by VARCHAR"))


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, _):
    if DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")    
        cursor.execute("PRAGMA synchronous=NORMAL")  
        cursor.execute("PRAGMA cache_size=-64000")  
        cursor.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
