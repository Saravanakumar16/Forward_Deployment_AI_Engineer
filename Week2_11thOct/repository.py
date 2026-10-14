
import json
from pathlib import Path
 
# Built from this file's location, so it works whichever folder you run from.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INVOICES_FILE = DATA_DIR / "invoices.json"
PAYMENTS_FILE = DATA_DIR / "payments.json"
 
 
class DataFileError(Exception):
    """A data file is missing, unreadable or not a JSON list."""
 
 
def _load(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            rows = json.load(f)
    except FileNotFoundError:
        raise DataFileError(f"Data file not found: {path}") from None
    except json.JSONDecodeError as e:
        raise DataFileError(f"{path.name} is not valid JSON: {e}") from None
    if not isinstance(rows, list):
        raise DataFileError(f"{path.name} must contain a JSON list.")
    return rows
 
 
def _save(path, rows):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=4)
    except OSError as e:
        raise DataFileError(f"Could not write {path.name}: {e}") from None
 
 
# ---------------------------------------------------------------- invoices
 
def load_invoices():
    return _load(INVOICES_FILE)
 
 
def invoice_exists(invoice_id):
    for invoice in load_invoices():
        if invoice.get("invoice_id") == invoice_id:
            return True
    return False
 
 
# ---------------------------------------------------------------- payments
 
def load_payments():
    return _load(PAYMENTS_FILE)
 
 
def save_payments(payments):
    _save(PAYMENTS_FILE, payments)
 
 
def get_payment_by_index(index):
    payments = load_payments()
    if 0 <= index < len(payments):
        return payments[index]
    return None
 
 
def add_payment(payment):
    """Append a payment and return its index."""
    payments = load_payments()
    payments.append(payment)
    save_payments(payments)
    return len(payments) - 1
 
 
def update_payment(index, payment):
    """Replace the payment at index. Returns False if there is no such index."""
    payments = load_payments()
    if not 0 <= index < len(payments):
        return False
    payments[index] = payment
    save_payments(payments)
    return True
 
 
def delete_payment(index):
    """Remove the payment at index and return it, or None if no such index."""
    payments = load_payments()
    if not 0 <= index < len(payments):
        return None
    removed = payments.pop(index)
    save_payments(payments)
    return removed
 
