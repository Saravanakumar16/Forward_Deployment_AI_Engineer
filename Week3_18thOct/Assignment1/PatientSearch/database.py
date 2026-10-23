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
SQL_DIR = os.path.join(os.path.dirname(PROJECT_DIR), "sql", "Day2")
ENV_FILE = os.path.join(SQL_DIR, ".env")

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
