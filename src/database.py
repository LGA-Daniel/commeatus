import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def get_engine():
    db_config = st.secrets["database"]
    # Construct connection string: postgresql://user:password@host:port/dbname
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
