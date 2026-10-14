# Diabetes Readmission Intervention Queue

**Testleaf Forward Deployed Engineer Program — Week 2 Mini Project**
Author: Saravanakumar

> ⚠️ **Learning prototype only.** The risk rule is a learning assumption, not a clinically validated model. It must not be used for real patient care decisions.

---

## 1. Business Problem

A hospital is concerned about diabetes patients being readmitted within 30 days of discharge. The care-management team has limited capacity and cannot review every discharged patient.

**The decision this MVP improves:**
> *Which recently discharged diabetes patients should the care-management team review first?*

The MVP turns historical encounter data into an operational workflow:

```
Load data → Score with an explainable rule → Prioritised queue → Track interventions → Measure against historical outcomes
```

---

## 2. Users

| User | What they need | Endpoint(s) |
|---|---|---|
| Care Management Team | A prioritised review queue, with reasons | `GET /care-queue`, `GET /care-queue/high`, `PATCH /interventions/{id}` |
| Hospital Operations | Queue volume and backlog | `GET /operations/summary` |
| Clinical Leadership | Why a patient was prioritised | `GET /encounters/{id}` (see `risk_reasons`) |
| Finance / Transformation | Is the queue worth scaling? | `GET /operations/readmission-analysis`, `GET /management/dashboard` |

---

## 3. FDE Discovery (before coding)

### What the dataset tells us
- **101,766** historical hospital encounters for **71,518** unique patients. One patient can have several encounters.
- Historical outcome (`readmitted`):

  | Value | Meaning | Count |
  |---|---|---|
  | `<30` | Readmitted within 30 days | 11,357 (11.16%) |
  | `>30` | Readmitted after 30 days | 35,545 |
  | `NO` | Not readmitted | 54,864 |

- Prior utilisation: inpatient, emergency and outpatient visits in the previous year.
- Treatment attributes: length of stay, number of medications, number of lab procedures.
- The 12 selected columns had **no missing values**. The loader still treats `?` and blanks as missing, to be safe.
- `age` is stored as a band, e.g. `[70-80)`, not a number.

### What we do NOT know
- Which readmissions were preventable.
- The cost of a readmission, or the cost of an intervention.
- The hospital's current discharge workflow and the care team's daily capacity.
- Whether the scoring rule is clinically valid.
- **Discharge dates.** The dataset has none, so "recently discharged" cannot be modelled; every encounter is treated as a candidate.

### MVP hypotheses
- Prior utilisation helps prioritise follow-up.
- Capacity is limited, so a risk-ordered queue is better than reviewing everyone.
- A simple rule is acceptable for an explainable first MVP.
- Historical outcomes can be used to evaluate the rule **after** scoring.

---

## 4. Prioritisation Rule

| Condition | Points |
|---|---|
| `number_inpatient >= 3` | +3 |
| `number_emergency >= 2` | +2 |
| `number_outpatient >= 3` | +1 |
| `time_in_hospital >= 7` | +1 |
| `num_medications >= 20` | +1 |

| Total score | Risk level |
|---|---|
| 0–2 | LOW |
| 3–4 | MEDIUM |
| 5 or more | HIGH |

**Example:** a patient with 4 inpatient visits (+3), 2 emergency visits (+2) and an 8-day stay (+1) scores **6 → HIGH**.

---

## 5. Key Design Decisions

1. **No data leakage.** `service.calculate_risk()` only receives five inputs (inpatient, emergency, outpatient, length of stay, medications). `readmitted` is not a parameter, so it cannot influence the score. It is read only by the evaluation queries in `repository.py`.
2. **Queue = MEDIUM + HIGH, excluding patients who cannot be contacted.** Encounters discharged as *Expired* (dispositions 11, 19, 20, 21) or to *Hospice* (13, 14) are left out of the queue. A care team should never be asked to phone a deceased patient. **285** MEDIUM/HIGH encounters were excluded for this reason.
3. **Queue is per encounter**, as the brief specifies. A patient with several encounters can appear more than once (see Limitations).
4. **Workflow rules** (in `service.py`):
   - Status can only move forward: `PENDING_REVIEW → ASSIGNED → CONTACTED → FOLLOW_UP_SCHEDULED → CLOSED`
   - `assigned_to` is required once a case leaves `PENDING_REVIEW`
   - A `CLOSED` case cannot be changed
5. **Audit trail (stretch goal).** An extra table, `intervention_history`, records every change. Each PATCH updates `care_interventions` **and** writes a history row in a single transaction.
6. **Repeatable load.** `data_loader.py` drops and recreates the tables, so it can be run any number of times for a clean start.
7. **Secrets kept out of GitHub.** The database password lives in `.env`, which is listed in `.gitignore`. `.env.example` shows the required setting without the real password.

---

## 6. Architecture

```
data/diabetic_data.csv
        │
        ▼
  data_loader.py ──── uses ────► service.calculate_risk()
        │
        ▼
   PostgreSQL (fde_db)
   ├── patient_encounters      (Table A)
   ├── care_interventions      (Table B)
   └── intervention_history    (stretch goal)
        ▲
  repository.py    ◄── ALL SQL lives here, parameterised with %s
        ▲
   service.py      ◄── risk rule, queue rules, workflow rules, metric maths
        ▲
    main.py        ◄── FastAPI routes, HTTP errors (400 / 404 / 422)
        ▲
  Swagger UI  (http://127.0.0.1:8000/docs)
```

### Project files

| File | Responsibility |
|---|---|
| `main.py` | FastAPI routes; converts service errors to HTTP 404 / 400 |
| `models.py` | Pydantic request/response models (invalid status → 422) |
| `service.py` | Business rules; raises `NotFoundError` / `BadRequestError` |
| `repository.py` | The **only** file containing SQL |
| `database.py` | Database connection settings, read from `.env` |
| `data_loader.py` | Repeatable CSV → PostgreSQL load |
| `01_schema.sql` | Table definitions with `CHECK` constraints *(the brief's `schema.sql`)* |
| `02_seed.sql` | Verification queries for the loaded data *(the brief's `seed_or_setup.sql`)* |
| `requirements.txt` | Python packages |
| `.env.example` | Template for the database setting (no real password) |
| `.gitignore` | Keeps `.env`, `.venv/` and `__pycache__/` out of GitHub |

---

## 7. Database Design

### Table A — `patient_encounters`
One row per hospital encounter: the 12 selected dataset columns plus `risk_score` and `risk_level`.
- `encounter_id` is the primary key.
- `CHECK` constraints limit `readmitted` to `NO / >30 / <30` and `risk_level` to `LOW / MEDIUM / HIGH`.

### Table B — `care_interventions`
One row per queued encounter.
- `encounter_id` is a **UNIQUE** foreign key, so there is one intervention per encounter.
- `status` is limited by a `CHECK` constraint to the five workflow values (default `PENDING_REVIEW`).
- `created_at` and `updated_at` timestamps.

### Stretch goal — `intervention_history`
`old_status`, `new_status`, `assigned_to`, `notes` and `changed_at` for every update.

---

## 8. API Endpoints

| Method | Endpoint | Purpose | Options / errors |
|---|---|---|---|
| GET | `/encounters` | List encounters (paginated) | `limit`, `offset`, `risk_level` |
| GET | `/encounters/{encounter_id}` | One encounter with risk reasons, intervention and history | 404 if not found |
| GET | `/care-queue` | MEDIUM + HIGH queue, highest score first | `min_score`, `status`, `limit`, `offset` |
| GET | `/care-queue/high` | HIGH-risk queue only | `status`, `limit`, `offset` |
| PATCH | `/interventions/{encounter_id}` | Update status / owner / notes | 404, 400, 422 |
| GET | `/operations/summary` | Volume and backlog | — |
| GET | `/operations/readmission-analysis` | Risk groups vs historical `<30` readmission | — |
| GET | `/management/dashboard` | Executive summary | — |

### Example request

```http
PATCH /interventions/67162368
Content-Type: application/json

{
  "status": "CONTACTED",
  "assigned_to": "Care Team A",
  "notes": "Follow-up appointment scheduled"
}
```

### Error handling

| Situation | Response |
|---|---|
| Encounter does not exist | **404** Encounter not found |
| Encounter is LOW risk or expired/hospice | **404** Not in the care queue |
| Invalid status, e.g. `"DONE"` | **422** Must be one of the 5 statuses |
| Status moves backwards | **400** Cannot move backwards |
| No fields sent | **400** Send at least one field |
| Leaving PENDING_REVIEW without `assigned_to` | **400** assigned_to is required |
| Changing a CLOSED case | **400** Already CLOSED |

---

## 9. How to Run (macOS)

### Prerequisites
- Python 3.10+
- PostgreSQL, with pgAdmin
- VS Code

### Step 1 — Create the database
In pgAdmin or psql:
```sql
CREATE DATABASE fde_db;
```

### Step 2 — Set up Python
From this project folder:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 3 — Add your database password
Copy `.env.example` to `.env` (in the same folder) and put in your own PostgreSQL password:
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/fde_db
```

### Step 4 — Load the data
Place `diabetic_data.csv` in the `data/` folder, then run:
```bash
python3 data_loader.py
```
Expected output:
```
Rows ready to load: 101766
Interventions created: 8253
HIGH: 2358  MEDIUM: 6180  LOW: 93228  Not contactable: 285
```

### Step 5 — Start the API
```bash
uvicorn main:app --reload
```
Open Swagger at **http://127.0.0.1:8000/docs**

### Step 6 (optional) — Check the data
Run `02_seed.sql` in pgAdmin's Query Tool on `fde_db`.

---

## 10. Results (calculated from the loaded data)

| Risk level | Encounters | Readmitted < 30 days | Readmission rate | Lift vs baseline |
|---|---|---|---|---|
| **HIGH** | 2,358 | 674 | **28.58%** | **2.56×** |
| **MEDIUM** | 6,180 | 1,335 | 21.60% | 1.94× |
| **LOW** | 93,228 | 9,348 | 10.03% | 0.90× |
| **All encounters** | 101,766 | 11,357 | **11.16%** | 1.00× |

- **Care queue:** 8,253 encounters, which is **8.11%** of all encounters. Their historical `<30` readmission rate is **24.21%**.
- **Capture rate:** the queue contains **17.59%** of all `<30` readmissions.

> **Headline:** HIGH-risk encounters were readmitted within 30 days at **2.56× the baseline rate**. Reviewing 8% of encounters reaches about 18% of historical readmissions.

---

## 11. Screenshots

### PostgreSQL — loaded records
*(Add your pgAdmin screenshot here)*

### FastAPI — Swagger UI
*(Add your Swagger screenshot here)*

---

## 12. Demo Video

*(Add your demo video link here)*

---

## 13. Limitations

- **Coverage.** 82% of `<30` readmissions fall in the LOW group, because most readmitted patients did not have heavy prior utilisation. The rule is a good *prioritiser* but a weak *screener*.
- **Per-encounter queue.** A patient with multiple encounters can appear more than once. A real product should keep one case per patient, using the latest discharge.
- **No discharge dates.** "Recently discharged" cannot be filtered.
- **Historical association, not causation.** The results show which groups were readmitted more often, not that an intervention would prevent it.
- **No authentication.** Anyone with access to the API can update interventions.

---

## 14. FDE Reflection

> *To the reviewer: these answers reflect my own understanding of the project.*

**1. What business problem did you solve?**
The care-management team has limited capacity and no systematic way to choose which discharged diabetes patients to review. This MVP gives them a ranked, explainable queue with workflow tracking, plus metrics that show whether the ranking points at the right patients.

**2. Who is the primary user?**
The care-management team, who work the queue every day. Hospital operations, clinical leadership and finance are secondary users of the metrics.

**3. What decision does your application improve?**
*Which discharged diabetes patient should we review next?* Instead of working in arbitrary order, the team starts with the encounters whose history (repeat admissions and emergency visits) is most associated with being readmitted.

**4. What did the dataset prove?**
- The rule separates risk well. HIGH-risk encounters were readmitted within 30 days at 28.6%, which is **2.56×** the 11.2% baseline. MEDIUM-risk encounters came in at 21.6%. The order HIGH > MEDIUM > LOW holds.
- The rule has a **coverage gap**. The queue is 8% of encounters but holds only about 18% of readmissions.
- These are historical associations; they do not prove that an intervention prevents readmission.

**5. What assumptions did you make?**
- The scoring weights and thresholds from the brief.
- Expired and hospice discharges are excluded from the queue.
- Each encounter is treated as a separate case.
- The intervention status only moves forward.
- The historical dataset is representative of the hospital's current patients.

**6. What must the hospital validate before this becomes a real product?**
- Clinical review of the rule and its thresholds.
- The team's real daily capacity, which sets how deep into the queue they can work.
- The cost of a readmission versus the cost of an intervention (the ROI case).
- Whether readmissions in the queue were actually preventable.
- Deduplication to one case per patient, and a live data feed with discharge dates.
- A pilot that compares outcomes with and without the intervention.
- Privacy, security and access controls for patient data.

**7. What would you use next: rules, traditional ML or an LLM? Why?**
**Traditional ML**, such as logistic regression or gradient boosting, trained on more features (diagnoses, A1C result, insulin changes, discharge disposition) with a proper train/test split. This should improve coverage of the readmissions the rule misses. Logistic regression stays explainable for clinical leadership.

I would keep the current rule as a transparent baseline that any model must beat. An LLM is not the right tool for scoring structured tabular risk, though it could later help summarise discharge notes for the care team.

---

## 15. Stretch Goals Completed

- ✅ Intervention history table (`intervention_history`) instead of overwriting the latest status
- ✅ Pagination (`limit`, `offset`) on encounters and the care queue
- ✅ Filtering by `risk_level`, `status` and `min_score`
- ✅ Risk reasons explaining each score
- ✅ Workflow validation rules (no backwards moves, owner required, closed cases locked)
