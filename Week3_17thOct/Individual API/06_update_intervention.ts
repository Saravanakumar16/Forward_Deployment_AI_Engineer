import type { InterventionUpdate, InterventionSummary } from "./01_interface.ts";

async function updateIntervention(encounterId: number, update: InterventionUpdate) {
  const response = await fetch(`http://localhost:8000/interventions/${encounterId}`, {
    method: "PATCH",                                  // GET is the default, so say PATCH
    headers: { "Content-Type": "application/json" },  // tell the API the body is JSON
    body: JSON.stringify(update),                     // turn the object into JSON text
  });

  // 400 = workflow rule broken, 404 = not found / not in queue, 422 = invalid status
  if (!response.ok) {
    const error = await response.json();
    throw new Error(`HTTP ${response.status}: ${JSON.stringify(error.detail)}`);
  }

  const i: InterventionSummary = await response.json();

  // The API also sends notes, created_at and updated_at.
  // Keep only the 4 fields I want to show.
  const intervention: InterventionSummary = {
    intervention_id: i.intervention_id,
    encounter_id: i.encounter_id,
    status: i.status,
    assigned_to: i.assigned_to,
  };

  return intervention;
}

async function main() {
  try {
    const data = await updateIntervention(79917156, {
      status: "ASSIGNED",
      assigned_to: "Care Team A",
      notes: "Picked up for review",
    });
    console.log(JSON.stringify(data, null, 2));
  } catch (error) {
    console.error((error as Error).message);
  }
}

main();
