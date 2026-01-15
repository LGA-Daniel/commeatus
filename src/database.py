import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

import os

def get_engine():
    # Check for env vars (Worker / Docker usage)
    if os.getenv("DB_HOST"):
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASS")
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT", "5432")
        dbname = os.getenv("DB_NAME", "commeatus_db")
    else:
        # Fallback to Streamlit secrets (Local Dev)
        db_config = st.secrets["database"]
        user = db_config["user"]
        password = db_config["password"]
        host = db_config["host"]
        port = db_config.get("port", 5432)
        dbname = db_config["dbname"]
    
    url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
    return create_engine(url)

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
