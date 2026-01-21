from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

BaseClinica = declarative_base()

# Local SQLite database file
DB_FILE = "clinica.db"

def get_engine_clinica():
    # Use 3 slashes for relative path (current dir)
    url = f"sqlite:///{DB_FILE}"
    # check_same_thread=False is needed for SQLite in multithreaded apps like Streamlit
    return create_engine(url, connect_args={"check_same_thread": False})

engine_clinica = get_engine_clinica()
SessionLocalClinica = sessionmaker(autocommit=False, autoflush=False, bind=engine_clinica)

def get_db_clinica():
    db = SessionLocalClinica()
    try:
        yield db
    finally:
        db.close()
