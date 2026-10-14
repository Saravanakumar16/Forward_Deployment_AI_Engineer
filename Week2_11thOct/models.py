from datetime import date
from typing import Optional
 
from pydantic import BaseModel, Field
 
 
class Invoice(BaseModel):
    invoice_id: str
    vendor: str
    amount: Optional[float] = None   # INV-106 has no amount in the data
    status: str
    date: date
 
 
class Payment(BaseModel):
    invoice_id: str = Field(min_length=1)
    paid: float = Field(gt=0)
 
 
class PaymentRecord(BaseModel):
    index: int
    invoice_id: str
    paid: float
 
