from pydantic import BaseModel

class InvoiceFormat(BaseModel):
       invoice_id: str
       vendor: str
       amount: float
       status: str
