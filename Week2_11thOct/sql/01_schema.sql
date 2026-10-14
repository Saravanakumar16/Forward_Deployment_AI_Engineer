-- schema.sql
-- Creates the tables for the Diabetes Readmission Intervention Queue.
-- WARNING: running this file drops the existing tables (fresh start).

DROP TABLE IF EXISTS intervention_history;
DROP TABLE IF EXISTS care_interventions;
DROP TABLE IF EXISTS patient_encounters;

-- Table A: one row per hospital encounter (focused subset of the dataset)
CREATE TABLE patient_encounters (
    encounter_id             INTEGER PRIMARY KEY,
    patient_nbr              INTEGER NOT NULL,
    age                      VARCHAR(10) NOT NULL,      -- age band, e.g. '[70-80)'
    time_in_hospital         INTEGER NOT NULL,
    number_inpatient         INTEGER NOT NULL,
    number_emergency         INTEGER NOT NULL,
    number_outpatient        INTEGER NOT NULL,
    num_medications          INTEGER NOT NULL,
    num_lab_procedures       INTEGER NOT NULL,
    discharge_disposition_id INTEGER NOT NULL,
    admission_type_id        INTEGER NOT NULL,
    readmitted               VARCHAR(5) NOT NULL        -- historical outcome: 'NO', '>30', '<30'
        CHECK (readmitted IN ('NO', '>30', '<30')),     -- used ONLY for evaluation, never for scoring
    risk_score               INTEGER NOT NULL,
    risk_level               VARCHAR(10) NOT NULL
        CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH'))
);

CREATE INDEX idx_encounters_risk_level ON patient_encounters (risk_level);
CREATE INDEX idx_encounters_patient_nbr ON patient_encounters (patient_nbr);

-- Table B: the care-management workflow (one row per queued encounter)
CREATE TABLE care_interventions (
    intervention_id SERIAL PRIMARY KEY,
    encounter_id    INTEGER NOT NULL UNIQUE
        REFERENCES patient_encounters (encounter_id),
    status          VARCHAR(30) NOT NULL DEFAULT 'PENDING_REVIEW'
        CHECK (status IN ('PENDING_REVIEW', 'ASSIGNED', 'CONTACTED',
                          'FOLLOW_UP_SCHEDULED', 'CLOSED')),
    assigned_to     VARCHAR(100),
    notes           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_interventions_status ON care_interventions (status);

-- Stretch goal: audit trail, one row for every change made through the API
CREATE TABLE intervention_history (
    history_id   SERIAL PRIMARY KEY,
    encounter_id INTEGER NOT NULL
        REFERENCES patient_encounters (encounter_id),
    old_status   VARCHAR(30),
    new_status   VARCHAR(30) NOT NULL,
    assigned_to  VARCHAR(100),
    notes        TEXT,
    changed_at   TIMESTAMP NOT NULL DEFAULT NOW()
);
