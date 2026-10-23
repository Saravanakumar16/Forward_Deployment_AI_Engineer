import type { ReadmissionAnalysis } from "./01_interface.ts";

async function getReadmissionAnalysis() {
  const response = await fetch("http://localhost:8000/operations/readmission-analysis");

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`HTTP ${response.status}: ${JSON.stringify(error.detail)}`);
  }

  const r: ReadmissionAnalysis = await response.json();

  // The API also sends by_risk_level, high_risk_readmission_rate,
  // queue_share_of_all_encounters and queue_capture_rate.
  // Keep only the 8 fields I want to show.
  const analysis: ReadmissionAnalysis = {
    total_encounters: r.total_encounters,
    total_readmitted_under_30_days: r.total_readmitted_under_30_days,
    baseline_readmission_rate: r.baseline_readmission_rate,
    high_risk_patients: r.high_risk_patients,
    high_risk_readmitted_under_30_days: r.high_risk_readmitted_under_30_days,
    queue_encounters: r.queue_encounters,
    queue_readmitted_under_30_days: r.queue_readmitted_under_30_days,
    queue_readmission_rate: r.queue_readmission_rate,
  };

  return analysis;
}

async function main() {
  try {
    const data = await getReadmissionAnalysis();
    console.log(JSON.stringify(data, null, 2));
  } catch (error) {
    console.error((error as Error).message);
  }
}

main();
