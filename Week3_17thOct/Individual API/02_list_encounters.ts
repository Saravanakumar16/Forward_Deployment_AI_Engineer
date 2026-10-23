import type { EncounterSummary, EncounterListResponse } from "./01_interface.ts";

async function getEncounters(limit: number, offset: number) {
  const response = await fetch(
    `http://localhost:8000/encounters?limit=${limit}&offset=${offset}`
  );
  const data: EncounterListResponse = await response.json();

  // The API sends every column. Keep only the 6 fields I want to show.
  const items: EncounterSummary[] = data.items.map((e) => ({
    encounter_id: e.encounter_id,
    patient_nbr: e.patient_nbr,
    age: e.age,
    readmitted: e.readmitted,
    risk_score: e.risk_score,
    risk_level: e.risk_level,
  }));

  return { total: data.total, limit: data.limit, offset: data.offset, items };
}

async function main() {
  const data = await getEncounters(5, 0);   // first 5 encounters
  console.log(JSON.stringify(data, null, 2));
}

main();
