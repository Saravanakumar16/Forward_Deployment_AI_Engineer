# repository.py
# ALL SQL lives in this file. Nothing else in the project writes SQL.
#
# Every query uses %s placeholders, and the values are passed separately to
# cursor.execute(). psycopg2 then escapes them safely, so user input is never
# concatenated into an SQL string (protects against SQL injection).

from psycopg2.extras import execute_values

from database import get_connection


# ---------------------------------------------------------------------------
# Setup / loading (used by data_loader.py)
# ---------------------------------------------------------------------------

def run_sql_file(file_path):
    """Run every statement in an .sql file (used to create the tables)."""
    with open(file_path, "r", encoding="utf-8") as f:
        sql_text = f.read()

    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql_text)
    finally:
        conn.close()


def insert_encounters(rows):
    """Bulk insert encounters. `rows` is a list of tuples in column order.

    execute_values sends the rows in batches of 1000, which is much faster
    than inserting 100,000 rows one at a time.
    """
    sql = """
        INSERT INTO patient_encounters (
            encounter_id, patient_nbr, age, time_in_hospital,
            number_inpatient, number_emergency, number_outpatient,
            num_medications, num_lab_procedures,
            discharge_disposition_id, admission_type_id,
            readmitted, risk_score, risk_level
        ) VALUES %s
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                execute_values(cur, sql, rows, page_size=1000)
    finally:
        conn.close()


def insert_encounter(encounter, add_to_queue):
    """Insert ONE encounter, and (optionally) its care-queue intervention.

    Both inserts run in ONE transaction: either both are saved or neither is.
    `encounter` is a dict with all patient_encounters columns.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO patient_encounters (
                        encounter_id, patient_nbr, age, time_in_hospital,
                        number_inpatient, number_emergency, number_outpatient,
                        num_medications, num_lab_procedures,
                        discharge_disposition_id, admission_type_id,
                        readmitted, risk_score, risk_level
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        encounter["encounter_id"],
                        encounter["patient_nbr"],
                        encounter["age"],
                        encounter["time_in_hospital"],
                        encounter["number_inpatient"],
                        encounter["number_emergency"],
                        encounter["number_outpatient"],
                        encounter["num_medications"],
                        encounter["num_lab_procedures"],
                        encounter["discharge_disposition_id"],
                        encounter["admission_type_id"],
                        encounter["readmitted"],
                        encounter["risk_score"],
                        encounter["risk_level"],
                    ),
                )
                saved = cur.fetchone()

                if add_to_queue:
                    cur.execute(
                        """
                        INSERT INTO care_interventions (encounter_id, status)
                        VALUES (%s, 'PENDING_REVIEW')
                        """,
                        (encounter["encounter_id"],),
                    )
        return saved
    finally:
        conn.close()


def create_queue_interventions(risk_levels, excluded_dispositions):
    """Create a PENDING_REVIEW intervention for every queue-eligible encounter.

    risk_levels           -> list like ['MEDIUM', 'HIGH']
    excluded_dispositions -> discharge_disposition_id values that cannot be
                             contacted (expired / hospice)
    Returns the number of interventions created.
    """
    sql = """
        INSERT INTO care_interventions (encounter_id, status)
        SELECT encounter_id, 'PENDING_REVIEW'
        FROM patient_encounters
        WHERE risk_level = ANY(%s)
          AND NOT (discharge_disposition_id = ANY(%s))
        ON CONFLICT (encounter_id) DO NOTHING
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, (risk_levels, excluded_dispositions))
                return cur.rowcount
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Encounters
# ---------------------------------------------------------------------------

def count_encounters(risk_level=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if risk_level is None:
                cur.execute("SELECT COUNT(*) AS total FROM patient_encounters")
            else:
                cur.execute(
                    "SELECT COUNT(*) AS total FROM patient_encounters WHERE risk_level = %s",
                    (risk_level,),
                )
            return cur.fetchone()["total"]
    finally:
        conn.close()


def list_encounters(limit, offset, risk_level=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if risk_level is None:
                cur.execute(
                    """
                    SELECT * FROM patient_encounters
                    ORDER BY encounter_id
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
            else:
                cur.execute(
                    """
                    SELECT * FROM patient_encounters
                    WHERE risk_level = %s
                    ORDER BY encounter_id
                    LIMIT %s OFFSET %s
                    """,
                    (risk_level, limit, offset),
                )
            return cur.fetchall()
    finally:
        conn.close()


def get_encounter(encounter_id):
    """Return one encounter as a dict, or None if it does not exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM patient_encounters WHERE encounter_id = %s",
                (encounter_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Patient search
# ---------------------------------------------------------------------------
# Each filter is optional. "(%s IS NULL OR column = %s)" means:
#   - filter value is None  -> condition is always true (filter ignored)
#   - filter value is given -> rows must match it
# So any combination of patient_nbr / risk_score / risk_level works,
# and values are still passed safely as %s parameters.

_SEARCH_WHERE = """
    WHERE (%s::BIGINT IS NULL OR patient_nbr = %s)
      AND (%s::INT    IS NULL OR risk_score  = %s)
      AND (%s::TEXT   IS NULL OR risk_level  = %s)
"""


def _search_params(patient_nbr, risk_score, risk_level):
    return (patient_nbr, patient_nbr, risk_score, risk_score, risk_level, risk_level)


def search_encounters(patient_nbr, risk_score, risk_level, limit, offset):
    """Return every encounter matching the filters (empty list if none)."""
    sql = (
        "SELECT * FROM patient_encounters"
        + _SEARCH_WHERE
        + " ORDER BY patient_nbr, encounter_id LIMIT %s OFFSET %s"
    )
    params = _search_params(patient_nbr, risk_score, risk_level) + (limit, offset)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def count_search_encounters(patient_nbr, risk_score, risk_level):
    sql = "SELECT COUNT(*) AS total FROM patient_encounters" + _SEARCH_WHERE
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, _search_params(patient_nbr, risk_score, risk_level))
            return cur.fetchone()["total"]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# High-risk patients with their intervention status
# ---------------------------------------------------------------------------
# LEFT JOIN keeps HIGH-risk encounters that have NO intervention row
# (not contactable). For those, i.status comes back as NULL.

_HIGH_RISK_FROM = """
    FROM patient_encounters e
    LEFT JOIN care_interventions i ON i.encounter_id = e.encounter_id
    WHERE e.risk_level = 'HIGH'
      AND (%s::BIGINT IS NULL OR e.patient_nbr = %s)
      AND (%s::TEXT   IS NULL OR i.status      = %s)
"""


def list_high_risk(patient_nbr, status, limit, offset):
    sql = (
        """
        SELECT e.encounter_id, e.patient_nbr, e.age, e.readmitted,
               e.risk_score, e.risk_level, e.discharge_disposition_id,
               i.status, i.assigned_to, i.updated_at
        """
        + _HIGH_RISK_FROM
        + " ORDER BY e.risk_score DESC, e.encounter_id LIMIT %s OFFSET %s"
    )
    params = (patient_nbr, patient_nbr, status, status, limit, offset)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def count_high_risk(patient_nbr, status):
    sql = "SELECT COUNT(*) AS total" + _HIGH_RISK_FROM
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, (patient_nbr, patient_nbr, status, status))
            return cur.fetchone()["total"]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Care queue and interventions
# ---------------------------------------------------------------------------

def get_care_queue(risk_levels, min_score, status, limit, offset):
    """Queue = encounters that have an intervention row, highest risk first.

    Optional filters: min_score and status (None means "no filter").
    """
    sql = """
        SELECT e.encounter_id, e.patient_nbr, e.age, e.risk_score, e.risk_level,
               e.number_inpatient, e.number_emergency, e.number_outpatient,
               e.time_in_hospital, e.num_medications,
               i.status, i.assigned_to, i.notes, i.updated_at
        FROM care_interventions i
        JOIN patient_encounters e ON e.encounter_id = i.encounter_id
        WHERE e.risk_level = ANY(%s)
          AND (%s IS NULL OR e.risk_score >= %s)
          AND (%s IS NULL OR i.status = %s)
        ORDER BY e.risk_score DESC, e.encounter_id
        LIMIT %s OFFSET %s
    """
    params = (risk_levels, min_score, min_score, status, status, limit, offset)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()


def count_care_queue(risk_levels, min_score, status):
    sql = """
        SELECT COUNT(*) AS total
        FROM care_interventions i
        JOIN patient_encounters e ON e.encounter_id = i.encounter_id
        WHERE e.risk_level = ANY(%s)
          AND (%s IS NULL OR e.risk_score >= %s)
          AND (%s IS NULL OR i.status = %s)
    """
    params = (risk_levels, min_score, min_score, status, status)

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()["total"]
    finally:
        conn.close()


def get_intervention(encounter_id):
    """Return the intervention for an encounter, or None."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM care_interventions WHERE encounter_id = %s",
                (encounter_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def update_intervention(encounter_id, old_status, new_status, assigned_to, notes):
    """Update the intervention AND write a history row in ONE transaction.

    `with conn:` commits both statements together, or rolls both back on error.
    """
    conn = get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE care_interventions
                    SET status = %s, assigned_to = %s, notes = %s, updated_at = NOW()
                    WHERE encounter_id = %s
                    RETURNING *
                    """,
                    (new_status, assigned_to, notes, encounter_id),
                )
                updated = cur.fetchone()

                cur.execute(
                    """
                    INSERT INTO intervention_history
                        (encounter_id, old_status, new_status, assigned_to, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (encounter_id, old_status, new_status, assigned_to, notes),
                )
        return updated
    finally:
        conn.close()


def get_intervention_history(encounter_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT old_status, new_status, assigned_to, notes, changed_at
                FROM intervention_history
                WHERE encounter_id = %s
                ORDER BY changed_at, history_id
                """,
                (encounter_id,),
            )
            return cur.fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Metrics (all calculated from stored data)
# ---------------------------------------------------------------------------

def count_by_risk_level():
    """Returns rows like {'risk_level': 'HIGH', 'total': 1234}."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT risk_level, COUNT(*) AS total
                FROM patient_encounters
                GROUP BY risk_level
                """
            )
            return cur.fetchall()
    finally:
        conn.close()


def count_by_status():
    """Returns rows like {'status': 'PENDING_REVIEW', 'total': 900}."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, COUNT(*) AS total
                FROM care_interventions
                GROUP BY status
                """
            )
            return cur.fetchall()
    finally:
        conn.close()


def count_not_contactable(risk_levels, excluded_dispositions):
    """MEDIUM/HIGH encounters kept OUT of the queue (expired / hospice)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS total
                FROM patient_encounters
                WHERE risk_level = ANY(%s)
                  AND discharge_disposition_id = ANY(%s)
                """,
                (risk_levels, excluded_dispositions),
            )
            return cur.fetchone()["total"]
    finally:
        conn.close()


# --- Evaluation queries: the ONLY place `readmitted` is read -----------------

def readmission_by_risk_level():
    """Historical <30-day readmissions per risk level (evaluation only)."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT risk_level,
                       COUNT(*) AS encounters,
                       SUM(CASE WHEN readmitted = '<30' THEN 1 ELSE 0 END) AS readmitted_under_30
                FROM patient_encounters
                GROUP BY risk_level
                """
            )
            return cur.fetchall()
    finally:
        conn.close()


def readmission_in_queue():
    """Historical <30-day readmissions among encounters in the care queue."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS encounters,
                       SUM(CASE WHEN e.readmitted = '<30' THEN 1 ELSE 0 END) AS readmitted_under_30
                FROM care_interventions i
                JOIN patient_encounters e ON e.encounter_id = i.encounter_id
                """
            )
            return cur.fetchone()
    finally:
        conn.close()
