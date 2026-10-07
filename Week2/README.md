# Invoice API (FastAPI + JSON file storage)

A small REST API for managing invoices, built with FastAPI. Invoices are stored in a JSON file on disk, so data is kept when the server restarts.

## Features

- List all invoices
- Get a single invoice by ID
- Create a new invoice
- Delete an invoice
- Data persisted in `data/invoices.json`

## Project structure

```
.
├── main.py              # Creates the FastAPI app and includes all routers
├── get_invoice.py       # GET routes
├── create_invoice.py    # POST route
├── delete_invoice.py    # DELETE route
├── data_store.py        # load_invoices() and save_invoices() helpers
├── models.py            # InvoiceFormat (Pydantic model)
├── data/
│   └── invoices.json    # Invoice data
└── README.md
```

## Setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install the dependencies:

   ```bash
   pip install fastapi uvicorn
   ```

## Run

From the folder that contains `main.py`:

```bash
uvicorn main:app --reload --port 8000
```

Swagger UI (interactive docs):

```
http://127.0.0.1:8000/docs
```

## Endpoints

| Method | Path                     | Description                | Success | Error                     |
|--------|--------------------------|----------------------------|---------|---------------------------|
| GET    | `/invoices`              | Return all invoices        | 200     |                           |
| GET    | `/invoices/{invoice_id}` | Return one invoice by ID   | 200     | Invoice not found message |
| POST   | `/invoices`              | Create a new invoice       | 200     | 422 if the body is invalid |
| DELETE | `/invoices/{invoice_id}` | Delete an invoice by ID    | 200     | 404 Invoice not found     |

## Invoice format

| Field        | Type   | Example     |
|--------------|--------|-------------|
| `invoice_id` | string | `"INV-103"` |
| `vendor`     | string | `"Nova Inc"` |
| `amount`     | number | `250000`    |
| `status`     | string | `"PENDING"` |

## Examples

### Get all invoices

```bash
curl http://127.0.0.1:8000/invoices
```

### Get one invoice

```bash
curl http://127.0.0.1:8000/invoices/INV-101
```

### Create an invoice

```bash
curl -X POST http://127.0.0.1:8000/invoices \
  -H "Content-Type: application/json" \
  -d '{"invoice_id": "INV-103", "vendor": "Nova Inc", "amount": 250000, "status": "PENDING"}'
```

### Delete an invoice

```bash
curl -X DELETE http://127.0.0.1:8000/invoices/INV-103
```

## How persistence works

Every request reads from or writes to `data/invoices.json`:

- **GET**: load the JSON file and return the data.
- **POST**: load invoices, add the new invoice, save the JSON file, return the created invoice.
- **DELETE**: load invoices, find the invoice, remove it, save the JSON file.

Because the data lives in a file and not in a Python list in memory, it is still there after the server is stopped and started again.

### Proving persistence

1. POST a new invoice.
2. Call GET `/invoices` and confirm it appears.
3. Stop Uvicorn (`CTRL+C`).
4. Start Uvicorn again.
5. Call GET `/invoices`. The new invoice is still there.
