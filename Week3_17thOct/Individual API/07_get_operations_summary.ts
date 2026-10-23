import type { OperationsSummary } from "./01_interface.ts";

async function getOperationsSummary() {
  const response = await fetch("http://localhost:8000/operations/summary");

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`HTTP ${response.status}: ${JSON.stringify(error.detail)}`);
  }

  const s: OperationsSummary = await response.json();

  // The API also sends excluded_not_contactable, pending / in-progress /
  // completed counts and by_status. Keep only the 5 fields I want to show.
  const summary: OperationsSummary = {
    total_encounters: s.total_encounters,
    high_risk: s.high_risk,
    medium_risk: s.medium_risk,
    low_risk: s.low_risk,
    queue_size: s.queue_size,
  };

  return summary;
}

async function main() {
  try {
    const data = await getOperationsSummary();
    console.log(JSON.stringify(data, null, 2));
  } catch (error) {
    console.error((error as Error).message);
  }
}

main();
