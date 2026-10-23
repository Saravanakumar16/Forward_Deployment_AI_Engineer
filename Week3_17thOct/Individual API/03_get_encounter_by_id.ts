import type { EncounterSummary } from "./01_interface.ts";

async function getEncounterById(id: number) {
  const response = await fetch(`http://localhost:8000/encounters/${id}`);

  // fetch does not throw on 404, so check the status myself
  if (!response.ok) {
    const error = await response.json();
    throw new Error(`HTTP ${response.status}: ${error.detail}`);
  }

  const e: EncounterSummary = await response.json();

  // The API sends every column plus risk reasons and intervention.
  // Keep only the 6 fields I want to show.
  const encounter: EncounterSummary = {
    encounter_id: e.encounter_id,
    patient_nbr: e.patient_nbr,
    age: e.age,
    readmitted: e.readmitted,
    risk_score: e.risk_score,
    risk_level: e.risk_level,
  };

  return encounter;
}

async function main() {
  try {
    const data = await getEncounterById(40926);
    console.log(JSON.stringify(data, null, 2));
  } catch (error) {
    console.error((error as Error).message);
  }
}

main();
