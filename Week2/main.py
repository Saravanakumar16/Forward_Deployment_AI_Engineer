import importlib
from fastapi import FastAPI

create_invoice = importlib.import_module("create_invoice").router
get_invoice = importlib.import_module("get_invoice").router
delete_invoice = importlib.import_module("delete_invoice").router

app = FastAPI()
app.include_router(create_invoice)
app.include_router(get_invoice)
app.include_router(delete_invoice)
