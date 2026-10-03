import csv

total_invoices = 0
processed_count = 0
invalid_count = 0
high_value_invoices = []
vendor_totals = {}

with open("data/homework_invoices.csv") as file:
    reader = csv.DictReader(file)
    columns = reader.fieldnames

    for invoice in reader:
        total_invoices += 1

        try:
            amount = float(invoice["amount"])
        except ValueError:
            invalid_count += 1
            print("Invalid amount, skipped:", invoice)
            continue

        processed_count += 1

        if amount > 100000:
            high_value_invoices.append(invoice)

        # Bonus: add this amount to the vendor's running total
        vendor = invoice["vendor"]

        if vendor in vendor_totals:
            vendor_totals[vendor] = vendor_totals[vendor] + amount
        else:
            vendor_totals[vendor] = amount

# Write the high-value invoices to a new CSV
with open("data/high_value_invoices.csv", "w", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=columns)
    writer.writeheader()
    writer.writerows(high_value_invoices)

print()
print("----- Summary -----")
print("Input invoices:", total_invoices)
print("Processed:", processed_count)
print("Invalid, reported:", invalid_count)
print("High-value:", len(high_value_invoices))

print()
print("----- Totals by vendor -----")
for vendor, total in vendor_totals.items():
    print(f"{vendor}: {total:,.2f}")
