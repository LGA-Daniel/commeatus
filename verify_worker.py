from src.database import engine, Base
from src.models import Pregao
from src.workers.import_pregoes import run_import_pregoes
from datetime import datetime, timedelta

# 1. Create tables if they don't exist
print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created (or already existed).")

# 2. Run a small test import (e.g., for yesterday)
print("Running test import...")
today = datetime.now()
yesterday = today - timedelta(days=1)
d_str = yesterday.strftime("%Y%m%d")

total, errors = run_import_pregoes(d_str, d_str)

print(f"Import finished. Total: {total}, Errors: {len(errors)}")
if errors:
    print("Errors:", errors)

# 3. Verify count
from sqlalchemy.orm import Session
with Session(engine) as session:
    count = session.query(Pregao).count()
    print(f"Total records in 'pregoes' table: {count}")
