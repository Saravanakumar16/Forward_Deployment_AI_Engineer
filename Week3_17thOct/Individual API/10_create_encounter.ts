import type { EncounterCreate, EncounterCreated } from "./01_interface.ts";

async function createEncounter(encounter: EncounterCreate) {
  const response = await fetch("http://localhost:8000/encounters", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(encounter),
  });

  // Confirm the response came from my Python API
  const backend = response.headers.get("X-Backend");   // set by main.py
  const server = response.headers.get("server");       // set by uvicorn
  console.log(`Status:     ${response.status} ${response.statusText}`);
  console.log(`X-Backend:  ${backend}`);
  console.log(`Server:     ${server}`);

  if (backend !== "Python FastAPI") {
    throw new Error("Response did NOT come from the Python API");
  }

  // 409 = encounter_id already exists, 422 = invalid data
  if (!response.ok) {
    const error = await response.json();
    throw new Error(`HTTP ${response.status}: ${JSON.stringify(error.detail)}`);
  }

  const e: EncounterCreated = await response.json();
  // Keep only the fields I want to show
  const created: EncounterCreated = {
    encounter_id: e.encounter_id,
    patient_nbr: e.patient_nbr,
    age: e.age,
    risk_score: e.risk_score,
    risk_level: e.risk_level,
    risk_reasons: e.risk_reasons,
    added_to_care_queue: e.added_to_care_queue,
    queue_message: e.queue_message,
  };
  return created;
}

async function main() {
  try {
    const data = await createEncounter({
      encounter_id: 999000001,
      patient_nbr: 888000001,
      age: "[60-70)",
      time_in_hospital: 8,
      number_inpatient: 4,
      number_emergency: 2,
      number_outpatient: 0,
      num_medications: 22,
      num_lab_procedures: 45,
      discharge_disposition_id: 1,
      admission_type_id: 1,
      readmitted: "NO",
    });
    console.log(JSON.stringify(data, null, 2));
  } catch (error) {
    console.error((error as Error).message);
  }
}

main();
