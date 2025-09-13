
import os
from pathlib import Path

from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "development")

db = SQLAlchemy()

# Base dir = repo root (adjust if your file sits elsewhere)
BASE_DIR = Path(__file__).resolve().parent

def normalize_sqlite_url(url: str) -> str:
    if url.startswith("sqlite:///"):
        # strip the sqlite prefix and resolve against BASE_DIR
        rel = url[len("sqlite:///"):]
        db_path = (BASE_DIR / rel).resolve()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # IMPORTANT: SQLite absolute file URLs must be POSIX style on Windows
        return "sqlite:///" + db_path.as_posix()
    return url

RAW_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///instance/app.db")
DATABASE_URL = normalize_sqlite_url(RAW_DATABASE_URL)

# Optional: print once to verify
print(DATABASE_URL)