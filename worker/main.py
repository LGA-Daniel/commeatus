import time
import os
import requests
import sys

# Add the parent directory to sys.path to import from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db

def main():
    print("Worker started...", flush=True)
    while True:
        print("Working...", flush=True)
        # Placeholder for data fetching
        time.sleep(10)

if __name__ == "__main__":
    main()
