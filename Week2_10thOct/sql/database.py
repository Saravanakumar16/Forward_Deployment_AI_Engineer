import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise SystemExit("DATABASE_URL is not set")

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        # Read all rows
        cur.execute("SELECT * FROM googlepay")
        for row in cur.fetchall():
            print(row)

        # Filtered query: pass values as parameters, never via f-strings
        cur.execute(
            "SELECT transaction_id, amount FROM googlepay WHERE status = %s",
            ("SUCCESS",),
        )
        print(cur.fetchall())
