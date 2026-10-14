-- seed_or_setup.sql
-- Step 1 (run ONCE as the postgres user, before anything else):
--
--     CREATE DATABASE fde_db;
--
-- Step 2: run schema.sql, then `python data_loader.py`.
--         The loader creates the tables, loads the CSV and builds the care queue.
--
-- Step 3 (optional): run the queries below in pgAdmin / psql to check the load.
--         These are good for the "PostgreSQL screenshot" deliverable.

-- How many encounters were loaded?
SELECT COUNT(*) AS total_encounters FROM patient_encounters;

-- How many encounters are in each risk level?
SELECT risk_level, COUNT(*) AS encounters
FROM patient_encounters
GROUP BY risk_level
ORDER BY risk_level;

-- Sample of the highest-risk encounters
SELECT encounter_id, patient_nbr, age, number_inpatient, number_emergency,
       number_outpatient, time_in_hospital, num_medications, risk_score, risk_level
FROM patient_encounters
ORDER BY risk_score DESC
LIMIT 10;

-- Care queue size by status
SELECT status, COUNT(*) AS interventions
FROM care_interventions
GROUP BY status;
