import sys
from unittest.mock import MagicMock

# Mock streamlit before importing src.database
sys.modules["streamlit"] = MagicMock()

import os
# Set env vars to avoid needing st.secrets
os.environ["DB_HOST"] = "localhost"
os.environ["DB_USER"] = "postgres" 
os.environ["DB_PASS"] = "postgres" # Assuming default from generic env or docker-compose, might fail if password differs
os.environ["DB_NAME"] = "commeatus_db"

# Now import
from src.database import engine, Base
from src.models import Pregao
from src.workers.import_pregoes import run_import_pregoes
from datetime import datetime, timedelta

# 1. Create tables if they don't exist
print("Creating tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("Tables created.")
except Exception as e:
    print(f"Error creating tables: {e}")
    # Don't exit, maybe they exist

# 2. Run test
print("Running test import (mocking UI callback)...")
today = datetime.now()
yesterday = today - timedelta(days=1)
d_str = yesterday.strftime("%Y%m%d")

# Mock callback
def cb(msg):
    print(f"[Callback] {msg}")

try:
    total, errors = run_import_pregoes(d_str, d_str, progress_callback=cb)
    print(f"Import finished. Total: {total}, Errors: {len(errors)}")
except Exception as e:
    print(f"Error running import: {e}")

# 3. Verify count
from sqlalchemy.orm import Session
try:
    with Session(engine) as session:
        count = session.query(Pregao).count()
        print(f"Total records in 'pregoes' table: {count}")
except Exception as e:
    print(f"Error checking DB: {e}")
