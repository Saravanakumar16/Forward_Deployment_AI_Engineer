# service.py
# Business rules live here: the risk rule, queue rules, workflow rules
# and the maths behind the metrics. No SQL and no HTTP code in this file.

import repository


# ---------------------------------------------------------------------------
# Business rule settings (learning assumptions, NOT clinical recommendations)
# ---------------------------------------------------------------------------

# Only these risk levels go into the care-management queue
QUEUE_RISK_LEVELS = ["MEDIUM", "HIGH"]

# Discharge dispositions where a follow-up call is not appropriate.
# From the dataset's IDs_mapping file:
#   11 = Expired, 19/20/21 = Expired (at home / in facility / place unknown)
#   13 = Hospice / home, 14 = Hospice / medical facility
NOT_CONTACTABLE_DISPOSITIONS = [11, 13, 14, 19, 20, 21]

# Workflow statuses in the order a case should move through them
STATUS_ORDER = [
    "PENDING_REVIEW",
    "ASSIGNED",
    "CONTACTED",
    "FOLLOW_UP_SCHEDULED",
    "CLOSED",
]


# ---------------------------------------------------------------------------
# Errors that main.py turns into HTTP responses
# ---------------------------------------------------------------------------

class NotFoundError(Exception):
    pass


class BadRequestError(Exception):
    pass


class ConflictError(Exception):
    pass


# ---------------------------------------------------------------------------
# 1. The prioritization rule
# ---------------------------------------------------------------------------

def calculate_risk(number_inpatient, number_emergency, number_outpatient,
                   time_in_hospital, num_medications):
    """Apply the prototype scoring rule.

    NOTE: this function does NOT receive `readmitted`. The historical outcome
    can never leak into the score because it is not even an input.

    Returns a dict: {"risk_score": int, "risk_level": str, "reasons": [str]}
    """
    score = 0
    reasons = []

    if number_inpatient >= 3:
        score = score + 3
        reasons.append("3+ prior inpatient visits (+3)")

    if number_emergency >= 2:
        score = score + 2
        reasons.append("2+ prior emergency visits (+2)")

    if number_outpatient >= 3:
        score = score + 1
        reasons.append("3+ prior outpatient visits (+1)")

    if time_in_hospital >= 7:
        score = score + 1
        reasons.append("Hospital stay of 7+ days (+1)")

    if num_medications >= 20:
        score = score + 1
        reasons.append("20+ medications (+1)")

    if score >= 5:
        level = "HIGH"
    elif score >= 3:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {"risk_score": score, "risk_level": level, "reasons": reasons}


def _risk_reasons_for(encounter):
    """Re-run the rule on a stored encounter to explain its score."""
    result = calculate_risk(
        encounter["number_inpatient"],
        encounter["number_emergency"],
        encounter["number_outpatient"],
        encounter["time_in_hospital"],
        encounter["num_medications"],
    )
    return result["reasons"]


def _percent(part, whole):
    """Safe percentage rounded to 2 decimals (avoids divide-by-zero)."""
    if whole == 0:
        return 0.0
    return round(part * 100.0 / whole, 2)


# ---------------------------------------------------------------------------
# 2. Encounters
# ---------------------------------------------------------------------------

def list_encounters(limit, offset, risk_level):
    items = repository.list_encounters(limit, offset, risk_level)
    total = repository.count_encounters(risk_level)
    return {"total": total, "limit": limit, "offset": offset, "items": items}


def create_encounter(data):
    """Business logic for adding ONE new encounter.

    `data` is a dict with the encounter fields from the request.
    Rules:
      - encounter_id must not already exist (409)
      - risk is calculated here with the SAME rule as the CSV loader,
        using only the 5 scoring fields (never `readmitted`)
      - MEDIUM/HIGH encounters go into the care queue as PENDING_REVIEW,
        unless the patient expired or went to hospice
    """
    if repository.get_encounter(data["encounter_id"]) is not None:
        raise ConflictError(f"Encounter {data['encounter_id']} already exists")

    risk = calculate_risk(
        data["number_inpatient"],
        data["number_emergency"],
        data["number_outpatient"],
        data["time_in_hospital"],
        data["num_medications"],
    )
    data["risk_score"] = risk["risk_score"]
    data["risk_level"] = risk["risk_level"]

    # Decide whether this encounter belongs in the care queue
    if risk["risk_level"] not in QUEUE_RISK_LEVELS:
        add_to_queue = False
        queue_message = "LOW risk - not added to the care queue"
    elif data["discharge_disposition_id"] in NOT_CONTACTABLE_DISPOSITIONS:
        add_to_queue = False
        queue_message = f"{risk['risk_level']} risk, but expired/hospice - not added to the care queue"
    else:
        add_to_queue = True
        queue_message = f"{risk['risk_level']} risk - added to the care queue as PENDING_REVIEW"

    saved = repository.insert_encounter(data, add_to_queue)

    saved["risk_reasons"] = risk["reasons"]
    saved["added_to_care_queue"] = add_to_queue
    saved["queue_message"] = queue_message
    return saved


def get_encounter(encounter_id):
    encounter = repository.get_encounter(encounter_id)
    if encounter is None:
        raise NotFoundError(f"Encounter {encounter_id} not found")

    encounter["risk_reasons"] = _risk_reasons_for(encounter)
    encounter["intervention"] = repository.get_intervention(encounter_id)
    encounter["intervention_history"] = repository.get_intervention_history(encounter_id)
    return encounter


def search_patients(patient_nbr, risk_score, risk_level, limit, offset):
    """Search encounters by patient number and/or risk score and/or risk level.

    Rules:
      - at least one filter must be given (400), otherwise it would just
        return the whole table - use GET /encounters for that
      - no match is NOT an error: total = 0 and items = [] (UI shows "No match")
      - more than one match: every matching encounter is returned
    """
    if patient_nbr is None and risk_score is None and risk_level is None:
        raise BadRequestError(
            "Give at least one search filter: patient_nbr, risk_score or risk_level"
        )

    items = repository.search_encounters(patient_nbr, risk_score, risk_level, limit, offset)
    total = repository.count_search_encounters(patient_nbr, risk_score, risk_level)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "filters": {
            "patient_nbr": patient_nbr,
            "risk_score": risk_score,
            "risk_level": risk_level,
        },
        "items": items,
    }


# ---------------------------------------------------------------------------
# 3. Care queue
# ---------------------------------------------------------------------------

def get_care_queue(risk_levels, min_score, status, limit, offset):
    if status is not None and status not in STATUS_ORDER:
        raise BadRequestError(f"Unknown status '{status}'. Use one of {STATUS_ORDER}")

    items = repository.get_care_queue(risk_levels, min_score, status, limit, offset)
    total = repository.count_care_queue(risk_levels, min_score, status)
    for item in items:
        item["risk_reasons"] = _risk_reasons_for(item)
    return {"total": total, "limit": limit, "offset": offset, "items": items}


# ---------------------------------------------------------------------------
# 4. Intervention workflow
# ---------------------------------------------------------------------------

def update_intervention(encounter_id, status, assigned_to, notes):
    """Update status / owner / notes for a queued encounter.

    Rules:
      - the encounter must exist (404)
      - it must be in the care queue, i.e. MEDIUM/HIGH and contactable (404)
      - at least one field must be sent (400)
      - status can move forward or stay the same, never backwards (400)
      - a CLOSED case cannot be changed (400)
    """
    if repository.get_encounter(encounter_id) is None:
        raise NotFoundError(f"Encounter {encounter_id} not found")

    current = repository.get_intervention(encounter_id)
    if current is None:
        raise NotFoundError(
            f"Encounter {encounter_id} is not in the care queue "
            "(LOW risk, or discharged to hospice / expired)"
        )

    if status is None and assigned_to is None and notes is None:
        raise BadRequestError("Send at least one of: status, assigned_to, notes")

    if current["status"] == "CLOSED":
        raise BadRequestError(f"Intervention for encounter {encounter_id} is already CLOSED")

    # Keep the existing value for any field that was not sent
    new_status = status if status is not None else current["status"]
    new_assigned_to = assigned_to if assigned_to is not None else current["assigned_to"]
    new_notes = notes if notes is not None else current["notes"]

    old_position = STATUS_ORDER.index(current["status"])
    new_position = STATUS_ORDER.index(new_status)
    if new_position < old_position:
        raise BadRequestError(
            f"Status cannot move backwards from {current['status']} to {new_status}"
        )

    # A case cannot be worked by nobody once it leaves PENDING_REVIEW
    if new_status != "PENDING_REVIEW" and not new_assigned_to:
        raise BadRequestError(f"assigned_to is required when status is {new_status}")

    return repository.update_intervention(
        encounter_id, current["status"], new_status, new_assigned_to, new_notes
    )


# ---------------------------------------------------------------------------
# 5. Metrics
# ---------------------------------------------------------------------------

def get_operations_summary():
    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    for row in repository.count_by_risk_level():
        risk_counts[row["risk_level"]] = row["total"]

    status_counts = {}
    for status in STATUS_ORDER:
        status_counts[status] = 0
    for row in repository.count_by_status():
        status_counts[row["status"]] = row["total"]

    queue_size = sum(status_counts.values())
    in_progress = (status_counts["ASSIGNED"]
                   + status_counts["CONTACTED"]
                   + status_counts["FOLLOW_UP_SCHEDULED"])

    return {
        "total_encounters": risk_counts["LOW"] + risk_counts["MEDIUM"] + risk_counts["HIGH"],
        "high_risk": risk_counts["HIGH"],
        "medium_risk": risk_counts["MEDIUM"],
        "low_risk": risk_counts["LOW"],
        "queue_size": queue_size,
        "excluded_not_contactable": repository.count_not_contactable(
            QUEUE_RISK_LEVELS, NOT_CONTACTABLE_DISPOSITIONS
        ),
        "pending_interventions": status_counts["PENDING_REVIEW"],
        "in_progress_interventions": in_progress,
        "completed_interventions": status_counts["CLOSED"],
        "by_status": status_counts,
    }


def get_readmission_analysis():
    """Compare the risk groups against the historical <30 day outcome.

    This runs AFTER scoring and only reads `readmitted` for evaluation.
    """
    rows = repository.readmission_by_risk_level()

    total_encounters = 0
    total_readmitted = 0
    for row in rows:
        total_encounters = total_encounters + row["encounters"]
        total_readmitted = total_readmitted + row["readmitted_under_30"]

    baseline_rate = _percent(total_readmitted, total_encounters)

    by_level = {}
    for row in rows:
        rate = _percent(row["readmitted_under_30"], row["encounters"])
        if baseline_rate > 0:
            lift = round(rate / baseline_rate, 2)
        else:
            lift = 0.0
        by_level[row["risk_level"]] = {
            "risk_level": row["risk_level"],
            "encounters": row["encounters"],
            "readmitted_under_30_days": row["readmitted_under_30"],
            "readmission_rate": rate,
            "lift_vs_baseline": lift,
        }

    # Always return the three levels in a fixed order
    by_risk_level = []
    for level in ["HIGH", "MEDIUM", "LOW"]:
        if level in by_level:
            by_risk_level.append(by_level[level])

    queue = repository.readmission_in_queue()
    queue_encounters = queue["encounters"]
    queue_readmitted = queue["readmitted_under_30"] or 0

    high = by_level.get("HIGH", {"encounters": 0, "readmitted_under_30_days": 0,
                                 "readmission_rate": 0.0})

    return {
        "total_encounters": total_encounters,
        "total_readmitted_under_30_days": total_readmitted,
        "baseline_readmission_rate": baseline_rate,
        "high_risk_patients": high["encounters"],
        "high_risk_readmitted_under_30_days": high["readmitted_under_30_days"],
        "high_risk_readmission_rate": high["readmission_rate"],
        "by_risk_level": by_risk_level,
        "queue_encounters": queue_encounters,
        "queue_readmitted_under_30_days": queue_readmitted,
        "queue_readmission_rate": _percent(queue_readmitted, queue_encounters),
        "queue_share_of_all_encounters": _percent(queue_encounters, total_encounters),
        "queue_capture_rate": _percent(queue_readmitted, total_readmitted),
    }


def get_management_dashboard():
    summary = get_operations_summary()
    analysis = get_readmission_analysis()

    high_lift = 0.0
    for row in analysis["by_risk_level"]:
        if row["risk_level"] == "HIGH":
            high_lift = row["lift_vs_baseline"]

    return {
        "total_encounters": summary["total_encounters"],
        "queue_size": summary["queue_size"],
        "queue_share_of_all_encounters": analysis["queue_share_of_all_encounters"],
        "open_interventions": summary["pending_interventions"] + summary["in_progress_interventions"],
        "completed_interventions": summary["completed_interventions"],
        "completion_rate": _percent(summary["completed_interventions"], summary["queue_size"]),
        "baseline_readmission_rate": analysis["baseline_readmission_rate"],
        "high_risk_readmission_rate": analysis["high_risk_readmission_rate"],
        "high_risk_lift_vs_baseline": high_lift,
        "queue_readmission_rate": analysis["queue_readmission_rate"],
        "queue_capture_rate": analysis["queue_capture_rate"],
        "headline": (
            f"Reviewing {analysis['queue_share_of_all_encounters']}% of encounters "
            f"reaches {analysis['queue_capture_rate']}% of historical <30-day readmissions. "
            f"HIGH-risk encounters were readmitted at {high_lift}x the baseline rate."
        ),
        "disclaimer": "Learning prototype only. Not for clinical decision-making.",
    }
