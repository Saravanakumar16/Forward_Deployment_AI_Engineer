import os
import psycopg
from dotenv import load_dotenv

load_dotenv()
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    raise SystemExit("DATABASE_URL is not set")

txn_id = "TXN-104"

with psycopg.connect(db_url) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM googlepay WHERE transaction_id = %s RETURNING *",
            (txn_id,),
        )
        deleted = cur.fetchone()
        if deleted:
            print("Deleted:", deleted)
        else:
            print(f"No record found with transaction_id {txn_id}")
