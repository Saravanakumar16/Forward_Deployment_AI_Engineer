// 12_get_high_risk_patients.ts
// 1. GET /patients/high-risk                         -> list HIGH-risk patients
// 2. GET /encounters/{id}/intervention-status        -> care status for one of them
//
// Run (API must be running on port 8000):
//   npx tsx 12_get_high_risk_patients.ts

type Status = "PENDING_REVIEW" | "ASSIGNED" | "CONTACTED" | "FOLLOW_UP_SCHEDULED" | "CLOSED";

interface HighRiskPatient {
  encounter_id: number;
  patient_nbr: number;
  age: string;
  risk_score: number;
  risk_level: "HIGH";
  in_care_queue: boolean;
  status: Status | null;
  assigned_to: string | null;
}

interface HighRiskPage {
  total: number;
  limit: number;
  offset: number;
  items: HighRiskPatient[];
}

interface HistoryEntry {
  old_status: string | null;
  new_status: string;
  assigned_to: string | null;
  notes: string | null;
  changed_at: string;
}

interface InterventionStatus {
  encounter_id: number;
  patient_nbr: number;
  risk_score: number;
  risk_level: string;
  risk_reasons: string[];
  in_care_queue: boolean;
  status: Status | null;
  assigned_to: string | null;
  notes: string | null;
  updated_at: string | null;
  history: HistoryEntry[];
  message: string;
}

const BASE_URL = "http://127.0.0.1:8000";

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  return response.json() as Promise<T>;
}

async function getHighRiskPatients(
  options: { patient_nbr?: number; status?: Status; limit?: number; offset?: number } = {}
): Promise<HighRiskPage> {
  const params = new URLSearchParams();
  if (options.patient_nbr !== undefined) params.append("patient_nbr", String(options.patient_nbr));
  if (options.status !== undefined) params.append("status", options.status);
  params.append("limit", String(options.limit ?? 50));
  params.append("offset", String(options.offset ?? 0));

  return getJson<HighRiskPage>(`${BASE_URL}/patients/high-risk?${params}`);
}

async function getInterventionStatus(encounterId: number): Promise<InterventionStatus> {
  return getJson<InterventionStatus>(`${BASE_URL}/encounters/${encounterId}/intervention-status`);
}

async function main() {
  try {
    // 1. First 5 HIGH-risk patients
    const page = await getHighRiskPatients({ limit: 5 });
    console.log(`\n=== HIGH-risk patients: ${page.total} in total (first 5) ===`);
    console.table(page.items.map((p) => ({
      encounter_id: p.encounter_id,
      patient_nbr: p.patient_nbr,
      risk_score: p.risk_score,
      status: p.status ?? "NOT IN QUEUE",
      assigned_to: p.assigned_to ?? "-",
    })));

    // 2. Care status for the first one in the list
    if (page.items.length > 0) {
      const id = page.items[0].encounter_id;
      const s = await getInterventionStatus(id);
      console.log(`\n=== Intervention status for encounter ${id} ===`);
      console.log("Message     :", s.message);
      console.log("Status      :", s.status ?? "NOT IN QUEUE");
      console.log("Assigned to :", s.assigned_to ?? "-");
      console.log("Notes       :", s.notes ?? "-");
      console.log("Risk reasons:", s.risk_reasons.join("; "));
      console.log("History     :", s.history.length ? "" : "no changes yet");
      s.history.forEach((h) =>
        console.log(`  ${h.changed_at}  ${h.old_status ?? "-"} -> ${h.new_status}  (${h.assigned_to ?? "-"})`)
      );
    }

    // 3. An encounter that does not exist -> 404
    await getInterventionStatus(1);
  } catch (error) {
    console.error("\nExpected error for encounter 1:", (error as Error).message);
  }
}

main();
