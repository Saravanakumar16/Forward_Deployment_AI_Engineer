from fastapi import APIRouter
from models import InvoiceFormat
from data_store import load_invoices, save_invoices

router = APIRouter()

@router.post("/invoices")
def create_invoice(invoice: InvoiceFormat):
    invoices = load_invoices()
    new_invoice = invoice.model_dump()
    invoices.append(new_invoice)
    save_invoices(invoices)
    return{"message":"Invoice created successfully","invoice": new_invoice}
