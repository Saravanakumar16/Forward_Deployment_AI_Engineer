from fastapi import HTTPException
from data_store import load_invoices, save_invoices
from fastapi import APIRouter

router = APIRouter()

@router.delete("/invoices/{invoice_id}")
def delete_invoice(invoice_id: str):
    invoices = load_invoices()
    for index, invoice in enumerate(invoices):
        if invoice["invoice_id"] == invoice_id:
           deleted = invoices.pop(index)
           save_invoices(invoices)
           return {"message": "Invoice deleted successfully", "invoice": deleted}


    raise HTTPException(
        status_code=404,
        detail="Invoice not found"
    )
