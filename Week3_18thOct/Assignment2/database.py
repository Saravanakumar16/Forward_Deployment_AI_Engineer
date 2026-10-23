# database.py
# Database configuration only. Every other file gets its connection from here.

import os

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Folder layout used for this project:
#   FDE - Week1/
#   ├── sql/Day2/.env              <- database settings live here
#   ├── sql/Day2/01_schema.sql
#   └── Week2_Day2_Home/           <- this Python code
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


def _find_env_file():
    """Look for sql/Day2/.env in this folder and every parent folder.

    Works no matter how deep the project folder is inside "FDE - Week1".
    """
    folder = PROJECT_DIR
    while True:
        candidate = os.path.join(folder, "sql", "Day2", ".env")
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(folder)
        if parent == folder:          # reached the top of the disk
            return None
        folder = parent


ENV_FILE = _find_env_file()
if ENV_FILE is None:
    raise RuntimeError(
        "Could not find sql/Day2/.env in this folder or any parent folder"
    )

# Read DATABASE_URL from sql/Day2/.env
load_dotenv(ENV_FILE)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/fde_db",
)


def get_connection():
    """Open a new PostgreSQL connection.

    RealDictCursor makes every row come back as a dictionary,
    e.g. row["encounter_id"], which is easy to turn into JSON.
    """
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
