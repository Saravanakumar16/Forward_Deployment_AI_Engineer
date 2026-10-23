// 01_interface.ts
// Shapes of the JSON returned by my FastAPI (field names must match the API exactly)

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export type Readmitted = "NO" | ">30" | "<30";

// One encounter - only the fields I want to show in the UI
export interface EncounterSummary {
  encounter_id: number;
  patient_nbr: number;
  age: string;              // age band, e.g. "[70-80)"
  readmitted: Readmitted;   // historical outcome
  risk_score: number;       // 0-8 points from the rule
  risk_level: RiskLevel;
}

// GET /encounters returns a page of encounters, not a plain list
export interface EncounterListResponse {
  total: number;            // total encounters matching the filter
  limit: number;
  offset: number;
  items: EncounterSummary[];
}

// ---------------------------------------------------------------------------
// Care queue
// ---------------------------------------------------------------------------

export type Status =
  | "PENDING_REVIEW"
  | "ASSIGNED"
  | "CONTACTED"
  | "FOLLOW_UP_SCHEDULED"
  | "CLOSED";

// One case in the care queue - only the fields I want to show in the UI
export interface CareQueueItem {
  encounter_id: number;
  patient_nbr: number;
  age: string;
  risk_level: RiskLevel;
  status: Status;
  assigned_to: string | null;   // null until the case is assigned
}

// GET /care-queue returns a page of cases
export interface CareQueueResponse {
  total: number;
  limit: number;
  offset: number;
  items: CareQueueItem[];
}

// ---------------------------------------------------------------------------
// Interventions
// ---------------------------------------------------------------------------

// What I SEND in the PATCH body - every field is optional
export interface InterventionUpdate {
  status?: Status;
  assigned_to?: string;
  notes?: string;
}

// What I want to SHOW from the PATCH response
export interface InterventionSummary {
  intervention_id: number;
  encounter_id: number;
  status: Status;
  assigned_to: string | null;
}

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------

// What I want to SHOW from GET /operations/summary
export interface OperationsSummary {
  total_encounters: number;
  high_risk: number;
  medium_risk: number;
  low_risk: number;
  queue_size: number;
}

// What I want to SHOW from GET /operations/readmission-analysis
export interface ReadmissionAnalysis {
  total_encounters: number;
  total_readmitted_under_30_days: number;
  baseline_readmission_rate: number;          // percent, e.g. 11.16
  high_risk_patients: number;
  high_risk_readmitted_under_30_days: number;
  queue_encounters: number;
  queue_readmitted_under_30_days: number;
  queue_readmission_rate: number;             // percent, e.g. 24.21
}

// What I want to SHOW from GET /management/dashboard
export interface ManagementDashboard {
  total_encounters: number;
  queue_size: number;
  open_interventions: number;         // PENDING_REVIEW + in progress
  completed_interventions: number;    // CLOSED
  high_risk_readmission_rate: number; // percent, e.g. 28.58
  high_risk_lift_vs_baseline: number; // times the baseline, e.g. 2.56
  queue_readmission_rate: number;     // percent, e.g. 24.21
  queue_capture_rate: number;         // percent of all <30 readmissions in the queue
}

// ---------------------------------------------------------------------------
// Create encounter (POST /encounters)
// ---------------------------------------------------------------------------

export type AgeBand =
  | "[0-10)" | "[10-20)" | "[20-30)" | "[30-40)" | "[40-50)"
  | "[50-60)" | "[60-70)" | "[70-80)" | "[80-90)" | "[90-100)";

// What I SEND - no risk_score / risk_level, the Python service calculates them
export interface EncounterCreate {
  encounter_id: number;
  patient_nbr: number;
  age: AgeBand;
  time_in_hospital: number;        // 1-14 days
  number_inpatient: number;
  number_emergency: number;
  number_outpatient: number;
  num_medications: number;
  num_lab_procedures: number;
  discharge_disposition_id: number;
  admission_type_id: number;
  readmitted?: Readmitted;         // optional, defaults to "NO"
}

// What I want to SHOW from the response
export interface EncounterCreated {
  encounter_id: number;
  patient_nbr: number;
  age: string;
  risk_score: number;
  risk_level: RiskLevel;
  risk_reasons: string[];
  added_to_care_queue: boolean;
  queue_message: string;
}
