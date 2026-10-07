from fastapi import APIRouter
from data_store import load_invoices

router = APIRouter()

@router.get("/invoices")
def get_invoice():
    return load_invoices()

@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    for invoice in load_invoices():
        if (invoice['invoice_id']) == invoice_id:
            return (invoice)
    return {"error":"Invoice not found"}
