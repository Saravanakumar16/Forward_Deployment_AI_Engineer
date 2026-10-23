import type { CareQueueItem, CareQueueResponse } from "./01_interface.ts";

async function getHighRiskQueue(limit: number, offset: number) {
  const response = await fetch(
    `http://localhost:8000/care-queue/high?limit=${limit}&offset=${offset}`
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`HTTP ${response.status}: ${JSON.stringify(error.detail)}`);
  }

  const data: CareQueueResponse = await response.json();

  // Keep only the 6 fields I want to show.
  const items: CareQueueItem[] = data.items.map((q) => ({
    encounter_id: q.encounter_id,
    patient_nbr: q.patient_nbr,
    age: q.age,
    risk_level: q.risk_level,
    status: q.status,
    assigned_to: q.assigned_to,
  }));

  return { total: data.total, limit: data.limit, offset: data.offset, items };
}

async function main() {
  try {
    const data = await getHighRiskQueue(5, 0);   // top 5 HIGH-risk cases
    console.log(JSON.stringify(data, null, 2));
  } catch (error) {
    console.error((error as Error).message);
  }
}

main();
