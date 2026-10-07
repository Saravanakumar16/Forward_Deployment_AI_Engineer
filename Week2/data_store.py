import json
from pathlib import Path

#DATA_FILE = Path(__file__).parent.parent/"data"/"invoices.json"

DATA_FILE = "../data/invoices.json"

def load_invoices():
    with open(DATA_FILE,"r") as f:
        return json.load(f)

def save_invoices(invoices):
    with open(DATA_FILE,"w") as f:
        json.dump(invoices, f, indent=2)
