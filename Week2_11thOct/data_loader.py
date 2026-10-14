# data_loader.py
# Loads the diabetes CSV into PostgreSQL in one repeatable run:
#   1. create the tables (schema.sql)
#   2. read only the columns we need from the CSV
#   3. clean each row and calculate the risk score (service.calculate_risk)
#   4. bulk insert the encounters
#   5. create PENDING_REVIEW interventions for the care queue
#
# Run:  python data_loader.py
# Optional: python data_loader.py data/other_file.csv
#
# NOTE: this is a FRESH load. It drops and recreates the tables,
#       so any intervention updates made through the API are reset.

import csv
import os
import sys

import repository
import service

from database import PROJECT_DIR, SQL_DIR

# CSV lives in Week2_Day2_Home/data, SQL files live in sql/Day2
DEFAULT_CSV = os.path.join(PROJECT_DIR, "data", "diabetic_data.csv")
SCHEMA_FILE = os.path.join(SQL_DIR, "01_schema.sql")

# The focused subset of columns we use (the CSV has 50)
INTEGER_COLUMNS = [
    "encounter_id",
    "patient_nbr",
    "time_in_hospital",
    "number_inpatient",
    "number_emergency",
    "number_outpatient",
    "num_medications",
    "num_lab_procedures",
    "discharge_disposition_id",
    "admission_type_id",
]
TEXT_COLUMNS = ["age", "readmitted"]
VALID_READMITTED = ["NO", ">30", "<30"]


def clean_value(value):
    """The dataset writes missing values as '?'. Treat those as None."""
    if value is None:
        return None
    value = value.strip()
    if value == "" or value == "?":
        return None
    return value


def clean_row(raw):
    """Turn one CSV row (dict of strings) into a clean dict.

    Returns (clean_dict, None) when OK, or (None, reason) when the row is skipped.
    """
    row = {}

    for col in INTEGER_COLUMNS:
        value = clean_value(raw.get(col))
        if value is None:
            return None, f"missing {col}"
        try:
            row[col] = int(value)
        except ValueError:
            return None, f"{col} is not a number"

    for col in TEXT_COLUMNS:
        value = clean_value(raw.get(col))
        if value is None:
            return None, f"missing {col}"
        row[col] = value

    if row["readmitted"] not in VALID_READMITTED:
        return None, "unknown readmitted value"

    return row, None


def load(csv_path):
    print(f"1. Creating tables from {SCHEMA_FILE}")
    repository.run_sql_file(SCHEMA_FILE)

    print(f"2. Reading {csv_path}")
    rows_to_insert = []
    seen_ids = set()
    skipped = {}

    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row, reason = clean_row(raw)

            if row is not None and row["encounter_id"] in seen_ids:
                row, reason = None, "duplicate encounter_id"

            if row is None:
                skipped[reason] = skipped.get(reason, 0) + 1
                continue

            seen_ids.add(row["encounter_id"])

            # Score using ONLY utilisation/treatment fields - never `readmitted`
            risk = service.calculate_risk(
                row["number_inpatient"],
                row["number_emergency"],
                row["number_outpatient"],
                row["time_in_hospital"],
                row["num_medications"],
            )

            rows_to_insert.append((
                row["encounter_id"],
                row["patient_nbr"],
                row["age"],
                row["time_in_hospital"],
                row["number_inpatient"],
                row["number_emergency"],
                row["number_outpatient"],
                row["num_medications"],
                row["num_lab_procedures"],
                row["discharge_disposition_id"],
                row["admission_type_id"],
                row["readmitted"],
                risk["risk_score"],
                risk["risk_level"],
            ))

    print(f"   Rows ready to load: {len(rows_to_insert)}")
    if skipped:
        print(f"   Rows skipped: {skipped}")
    else:
        print("   Rows skipped: 0")

    print("3. Inserting encounters into patient_encounters")
    repository.insert_encounters(rows_to_insert)

    print("4. Building the care queue (MEDIUM + HIGH, excluding expired/hospice)")
    created = repository.create_queue_interventions(
        service.QUEUE_RISK_LEVELS, service.NOT_CONTACTABLE_DISPOSITIONS
    )
    print(f"   Interventions created: {created}")

    summary = service.get_operations_summary()
    print("Done.")
    print(f"   HIGH: {summary['high_risk']}  MEDIUM: {summary['medium_risk']}  "
          f"LOW: {summary['low_risk']}  Not contactable: {summary['excluded_not_contactable']}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = DEFAULT_CSV

    if not os.path.exists(path):
        print(f"CSV not found: {path}")
        print("Put diabetic_data.csv inside the data/ folder.")
        sys.exit(1)

    load(path)
