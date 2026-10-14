import repository
 
CANCELLED = "CANCELLED"
 
 
class NotFoundError(Exception):
    """The requested record does not exist (the API answers 404)."""
 
 
class BusinessRuleError(Exception):
    """The request breaks a business rule (the API answers 400)."""
 
 
# ------------------------------------------------------------------ helpers
 
def _amount(invoice):
    """The invoice amount as a number, or None if it is missing or not numeric."""
    value = invoice.get("amount")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value
 
 
def _counts_in_totals(invoice):
    """Rows with no amount, cancelled rows and unmatched credit notes don't count."""
    amount = _amount(invoice)
    return amount is not None and amount > 0 and invoice.get("status") != CANCELLED
 
 
# ------------------------------------------------------- task 1: normalize
 
def normalize_invoices(invoices):
    """Clean vendor and status in place. Returns the indexes where amount is None."""
    missing_amount = []
    for index in range(len(invoices)):
        invoices[index]["vendor"] = str(invoices[index].get("vendor") or "").strip().title()
        invoices[index]["status"] = str(invoices[index].get("status") or "").strip().upper()
        if _amount(invoices[index]) is None:
            missing_amount.append(index)
    return missing_amount
 
 
# ------------------------------------------------ task 2: exact duplicates
 
def remove_exact_duplicates(invoices):
    """Remove rows where every field matches an earlier row.
 
    Returns (exact_dupes, removed): exact_dupes maps each duplicated key to
    the list of its indexes, removed is the list of indexes that were deleted.
    """
    groups = {}
    for index, invoice in enumerate(invoices):
        key = tuple(sorted(invoice.items()))        # every field, in a fixed order
        groups.setdefault(key, []).append(index)
 
    exact_dupes = {key: indexes for key, indexes in groups.items() if len(indexes) > 1}
 
    removed = []
    for indexes in exact_dupes.values():
        removed.extend(indexes[1:])                 # keep the first row of each group
 
    # Delete from the end, so the indexes still waiting to be deleted don't shift.
    for index in sorted(removed, reverse=True):
        del invoices[index]
 
    return exact_dupes, sorted(removed)
 
 
# -------------------------------------------- task 3: suspected duplicates
 
def find_suspected_duplicates(invoices):
    """Pairs of invoice ids where vendor, amount and date match but the id differs."""
    groups = {}
    for index, invoice in enumerate(invoices):
        if _amount(invoice) is None:
            continue
        key = (invoice.get("vendor"), _amount(invoice), invoice.get("date"))
        groups.setdefault(key, []).append(index)
 
    pairs = []
    for indexes in groups.values():
        for position, later in enumerate(indexes):
            for earlier in indexes[:position]:
                later_id = invoices[later].get("invoice_id")
                earlier_id = invoices[earlier].get("invoice_id")
                if later_id != earlier_id:
                    pairs.append((later_id, earlier_id))
    return pairs
 
 
# ---------------------------------------------------- task 4: credit notes
 
def apply_credit_notes(invoices):
    """Match each negative invoice to a positive one (same vendor, same absolute amount).
 
    Marks both rows CANCELLED in place. Returns (pairs, unmatched): pairs is a
    list of (credit_index, partner_index), unmatched is the list of indexes of
    credit notes that have no partner.
    """
    pairs = []
    unmatched = []
    used = set()
 
    for index, invoice in enumerate(invoices):
        amount = _amount(invoice)
        if amount is None or amount >= 0:
            continue
 
        partner = None
        for other_index, other in enumerate(invoices):
            if other_index in used or other.get("status") == CANCELLED:
                continue
            if other.get("vendor") == invoice.get("vendor") and _amount(other) == -amount:
                partner = other_index
                break
 
        if partner is None:
            unmatched.append(index)
            continue
 
        used.update((index, partner))
        invoices[index]["status"] = CANCELLED
        invoices[partner]["status"] = CANCELLED
        pairs.append((index, partner))
 
    return pairs, unmatched
 
 
def vendor_totals(invoices):
    totals = {}
    for invoice in invoices:
        if _counts_in_totals(invoice):
            vendor = invoice["vendor"]
            totals[vendor] = totals.get(vendor, 0) + _amount(invoice)
    return totals
 
 
# ------------------------------------------------------ task 5: reconcile
 
def reconcile(invoices, payments):
    """Join payments to invoices by invoice_id and compare billed against paid."""
    billed = {}
    for invoice in invoices:
        if _counts_in_totals(invoice):
            invoice_id = invoice.get("invoice_id")
            billed[invoice_id] = billed.get(invoice_id, 0) + _amount(invoice)
 
    paid = {}
    for payment in payments:
        invoice_id = payment.get("invoice_id")
        paid[invoice_id] = paid.get(invoice_id, 0) + (payment.get("paid") or 0)
 
    lines = []
    for invoice_id, amount in billed.items():
        total_paid = paid.get(invoice_id, 0)
        balance = round(amount - total_paid, 2)
        if total_paid == 0:
            status = "UNPAID"
        elif balance > 0:
            status = "PARTIAL"
        elif balance == 0:
            status = "PAID"
        else:
            status = "OVERPAID"
        lines.append({
            "invoice_id": invoice_id,
            "billed": amount,
            "paid": total_paid,
            "balance": balance,
            "status": status,
        })
 
    all_invoice_ids = {invoice.get("invoice_id") for invoice in invoices}
    unmatched_payments = []
    for invoice_id, total_paid in paid.items():
        if invoice_id in billed:
            continue
        if invoice_id in all_invoice_ids:
            reason = "invoice is cancelled or has no amount"
        else:
            reason = "no such invoice"
        unmatched_payments.append({"invoice_id": invoice_id, "paid": total_paid, "reason": reason})
 
    return {"invoices": lines, "unmatched_payments": unmatched_payments}
 
 
# ------------------------------------------------------- tasks 1-5 together
 
def build_invoice_report():
    """Run tasks 1-4 on the invoices. Each step works on the result of the one before."""
    invoices = repository.load_invoices()
 
    missing = normalize_invoices(invoices)
    missing_amount = [{"index": i, "invoice_id": invoices[i].get("invoice_id")} for i in missing]
 
    exact_dupes, removed = remove_exact_duplicates(invoices)
    exact_duplicates = [
        {"invoice_id": dict(key).get("invoice_id"), "indexes": indexes, "removed": indexes[1:]}
        for key, indexes in exact_dupes.items()
    ]
 
    suspected = find_suspected_duplicates(invoices)
    pairs, unmatched = apply_credit_notes(invoices)
 
    return {
        "missing_amount": missing_amount,
        "exact_duplicates": exact_duplicates,
        "suspected_duplicates": [f"{later} ~ {earlier}" for later, earlier in suspected],
        "cancelled_pairs": [f"{credit} <-> {partner}" for credit, partner in pairs],
        "unmatched_credit_notes": [
            {"index": i, "invoice_id": invoices[i].get("invoice_id")} for i in unmatched
        ],
        "vendor_totals": vendor_totals(invoices),
        "invoices": invoices,
    }
 
 
def build_reconciliation():
    """Task 5: reconcile the payments against the cleaned invoices."""
    invoices = build_invoice_report()["invoices"]
    return reconcile(invoices, repository.load_payments())
 
 
def print_report():
    report = build_invoice_report()
 
    print("1) Normalize")
    for row in report["missing_amount"]:
        print(f"   Amount is None at index {row['index']} ({row['invoice_id']}) - excluded from totals")
    if not report["missing_amount"]:
        print("   Every row has an amount")
 
    print("2) Exact duplicates")
    for group in report["exact_duplicates"]:
        print(f"   {group['invoice_id']}: indexes {group['indexes']} - "
              f"kept {group['indexes'][0]}, removed {group['removed']}")
    if not report["exact_duplicates"]:
        print("   None found")
 
    print("3) Suspected duplicates")
    for pair in report["suspected_duplicates"]:
        print(f"   ({pair})")
    if not report["suspected_duplicates"]:
        print("   None found")
 
    print("4) Credit notes")
    for pair in report["cancelled_pairs"]:
        print(f"   {pair}")
    for row in report["unmatched_credit_notes"]:
        print(f"   Credit note at index {row['index']} ({row['invoice_id']}) has no partner - "
              f"left as is, excluded from totals")
    if not report["cancelled_pairs"] and not report["unmatched_credit_notes"]:
        print("   No credit notes")
 
    print("   Vendor totals")
    for vendor, total in report["vendor_totals"].items():
        print(f"   {vendor:<15}{total:>12,.2f}")
 
    print("5) Reconciliation")
    reconciliation = reconcile(report["invoices"], repository.load_payments())
    print(f"   {'invoice':<10}{'billed':>12}{'paid':>12}{'balance':>12}  status")
    for line in reconciliation["invoices"]:
        print(f"   {line['invoice_id']:<10}{line['billed']:>12,.2f}{line['paid']:>12,.2f}"
              f"{line['balance']:>12,.2f}  {line['status']}")
    for row in reconciliation["unmatched_payments"]:
        print(f"   Payment of {row['paid']:,.2f} for {row['invoice_id']}: {row['reason']}")
 
 
# ----------------------------------------------------------- payments CRUD
 
def _validated_payment(data):
    """Apply the payment rules and return a clean dict ready to store."""
    invoice_id = str(data.get("invoice_id") or "").strip()
    paid = data.get("paid")
 
    if not invoice_id:
        raise BusinessRuleError("invoice_id is required.")
    if isinstance(paid, bool) or not isinstance(paid, (int, float)) or paid <= 0:
        raise BusinessRuleError("paid must be a number greater than 0.")
    if not repository.invoice_exists(invoice_id):
        raise BusinessRuleError(f"Invoice {invoice_id} does not exist.")
 
    return {"invoice_id": invoice_id, "paid": paid}
 
 
def list_payments(invoice_id=None):
    payments = []
    for index, payment in enumerate(repository.load_payments()):
        if invoice_id is None or payment.get("invoice_id") == invoice_id:
            payments.append({"index": index, **payment})
    return payments
 
 
def get_payment(index):
    payment = repository.get_payment_by_index(index)
    if payment is None:
        raise NotFoundError(f"Payment with index {index} not found.")
    return {"index": index, **payment}
 
 
def create_payment(data):
    payment = _validated_payment(data)
    index = repository.add_payment(payment)
    return {"index": index, **payment}
 
 
def update_payment(index, data):
    if repository.get_payment_by_index(index) is None:
        raise NotFoundError(f"Payment with index {index} not found.")
    payment = _validated_payment(data)
    repository.update_payment(index, payment)
    return {"index": index, **payment}
 
 
def delete_payment(index):
    removed = repository.delete_payment(index)
    if removed is None:
        raise NotFoundError(f"Payment with index {index} not found.")
    return removed
 
 
if __name__ == "__main__":
    print_report()
 
