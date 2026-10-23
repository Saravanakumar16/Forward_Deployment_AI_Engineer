// 11_search_patients.ts
// Calls GET /patients/search and prints the matches.
//
// Run (API must be running on port 8000):
//   npx tsx 11_search_patients.ts

type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

// Filters - every one is optional, but at least one must be given
interface PatientSearchFilters {
  patient_nbr?: number;
  risk_score?: number;     // 0 - 8
  risk_level?: RiskLevel;
}

// One row returned by the API (only the fields we display)
interface PatientSearchRow {
  encounter_id: number;
  patient_nbr: number;
  age: string;
  readmitted: string;
  risk_score: number;
  risk_level: RiskLevel;
}

interface PatientSearchResponse {
  total: number;
  limit: number;
  offset: number;
  items: PatientSearchRow[];
}

const BASE_URL = "http://127.0.0.1:8000";

async function searchPatients(
  filters: PatientSearchFilters,
  limit = 100,
  offset = 0
): Promise<PatientSearchResponse> {
  // Only add the filters that were actually given
  const params = new URLSearchParams();
  if (filters.patient_nbr !== undefined) params.append("patient_nbr", String(filters.patient_nbr));
  if (filters.risk_score !== undefined) params.append("risk_score", String(filters.risk_score));
  if (filters.risk_level !== undefined) params.append("risk_level", filters.risk_level);
  params.append("limit", String(limit));
  params.append("offset", String(offset));

  const response = await fetch(`${BASE_URL}/patients/search?${params.toString()}`);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`HTTP ${response.status}: ${detail}`);
  }

  const data = await response.json();

  // The API sends every column. Keep only the 6 fields we show.
  const items: PatientSearchRow[] = data.items.map((e: PatientSearchRow) => ({
    encounter_id: e.encounter_id,
    patient_nbr: e.patient_nbr,
    age: e.age,
    readmitted: e.readmitted,
    risk_score: e.risk_score,
    risk_level: e.risk_level,
  }));

  return { total: data.total, limit: data.limit, offset: data.offset, items };
}

function printResult(title: string, result: PatientSearchResponse): void {
  console.log(`\n=== ${title} ===`);
  if (result.total === 0) {
    console.log("No match");
    return;
  }
  console.log(`${result.total} match(es)`);
  console.table(result.items);
}

async function main() {
  try {
    // 1. By patient number only - can return several encounters
    printResult("patient_nbr = 8222157",
      await searchPatients({ patient_nbr: 8222157 }));

    // 2. By risk level only (first 5)
    printResult("risk_level = HIGH (first 5)",
      await searchPatients({ risk_level: "HIGH" }, 5));

    // 3. Risk score AND risk level together (first 5)
    printResult("risk_score = 5 AND risk_level = HIGH (first 5)",
      await searchPatients({ risk_score: 5, risk_level: "HIGH" }, 5));

    // 4. A patient that does not exist - should print "No match"
    printResult("patient_nbr = 1 (does not exist)",
      await searchPatients({ patient_nbr: 1 }));

    // 5. No filters - the API should reject it with HTTP 400
    await searchPatients({});
  } catch (error) {
    console.error("\nExpected error for 'no filters':", (error as Error).message);
  }
}

main();
