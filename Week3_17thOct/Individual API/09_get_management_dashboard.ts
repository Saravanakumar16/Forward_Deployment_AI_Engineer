import type { ManagementDashboard } from "./01_interface.ts";

async function getManagementDashboard() {
  const response = await fetch("http://localhost:8000/management/dashboard");

  if (!response.ok) {
    const error = await response.json();
    throw new Error(`HTTP ${response.status}: ${JSON.stringify(error.detail)}`);
  }

  const d: ManagementDashboard = await response.json();

  // The API also sends queue_share_of_all_encounters, completion_rate,
  // baseline_readmission_rate, headline and disclaimer.
  // Keep only the 8 fields I want to show.
  const dashboard: ManagementDashboard = {
    total_encounters: d.total_encounters,
    queue_size: d.queue_size,
    open_interventions: d.open_interventions,
    completed_interventions: d.completed_interventions,
    high_risk_readmission_rate: d.high_risk_readmission_rate,
    high_risk_lift_vs_baseline: d.high_risk_lift_vs_baseline,
    queue_readmission_rate: d.queue_readmission_rate,
    queue_capture_rate: d.queue_capture_rate,
  };

  return dashboard;
}

async function main() {
  try {
    const data = await getManagementDashboard();
    console.log(JSON.stringify(data, null, 2));
  } catch (error) {
    console.error((error as Error).message);
  }
}

main();
