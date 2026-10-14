from typing import List, Optional
 
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
 
import services
from models import Payment, PaymentRecord
from repository import DataFileError
from services import BusinessRuleError, NotFoundError
 
app = FastAPI(title="Invoices and Payments API")
 
 
# ----------------------------------------------------------- error handling
# One handler per error type, instead of a try/except in every endpoint.
 
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})
 
 
@app.exception_handler(BusinessRuleError)
async def business_rule_handler(request: Request, exc: BusinessRuleError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
 
 
@app.exception_handler(DataFileError)
async def data_file_handler(request: Request, exc: DataFileError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})
 
 
# ----------------------------------------------------------------- payments
 
@app.get("/payments", response_model=List[PaymentRecord])
def read_payments(invoice_id: Optional[str] = None):
    return services.list_payments(invoice_id)
 
 
@app.get("/payments/{payment_index}", response_model=PaymentRecord)
def read_payment(payment_index: int):
    return services.get_payment(payment_index)
 
 
@app.post("/payments", response_model=PaymentRecord, status_code=201)
def create_new_payment(payment: Payment):
    return services.create_payment(payment.model_dump())
 
 
@app.put("/payments/{payment_index}", response_model=PaymentRecord)
def update_existing_payment(payment_index: int, payment: Payment):
    return services.update_payment(payment_index, payment.model_dump())
 
 
@app.delete("/payments/{payment_index}")
def delete_existing_payment(payment_index: int):
    removed = services.delete_payment(payment_index)
    return {"detail": "Payment deleted successfully", "payment": removed}
 
 
# ------------------------------------------------------------------ reports
 
@app.get("/invoices/report")
def read_invoice_report():
    """Tasks 1-4: normalize, exact duplicates, suspected duplicates, credit notes."""
    return services.build_invoice_report()
 
 
@app.get("/reconciliation")
def read_reconciliation():
    """Task 5: billed against paid for each invoice."""
    return services.build_reconciliation()
 
