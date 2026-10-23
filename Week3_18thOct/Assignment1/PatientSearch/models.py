# models.py
# Pydantic models: the shape of the data going in and out of the API.
# FastAPI uses these to validate requests and to document Swagger.

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# Allowed workflow statuses. A request with any other value gets a 422 error.
Status = Literal["PENDING_REVIEW", "ASSIGNED", "CONTACTED", "FOLLOW_UP_SCHEDULED", "CLOSED"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]

# The 10 age bands used in the dataset
AgeBand = Literal["[0-10)", "[10-20)", "[20-30)", "[30-40)", "[40-50)",
                  "[50-60)", "[60-70)", "[70-80)", "[80-90)", "[90-100)"]


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

class InterventionUpdate(BaseModel):
    status: Optional[Status] = None
    assigned_to: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=2000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "CONTACTED",
                "assigned_to": "Care Team A",
                "notes": "Follow-up appointment scheduled",
            }
        }
    }


class EncounterCreate(BaseModel):
    """Body for POST /encounters.

    risk_score and risk_level are NOT accepted here - the service calculates them.
    """
    encounter_id: int = Field(gt=0)
    patient_nbr: int = Field(gt=0)
    age: AgeBand
    time_in_hospital: int = Field(ge=1, le=14)           # dataset range: 1-14 days
    number_inpatient: int = Field(ge=0)
    number_emergency: int = Field(ge=0)
    number_outpatient: int = Field(ge=0)
    num_medications: int = Field(ge=0)
    num_lab_procedures: int = Field(ge=0)
    discharge_disposition_id: int = Field(gt=0)
    admission_type_id: int = Field(gt=0)
    readmitted: Literal["NO", ">30", "<30"] = "NO"       # historical outcome, never used for scoring

    model_config = {
        "json_schema_extra": {
            "example": {
                "encounter_id": 999000001,
                "patient_nbr": 888000001,
                "age": "[60-70)",
                "time_in_hospital": 8,
                "number_inpatient": 4,
                "number_emergency": 2,
                "number_outpatient": 0,
                "num_medications": 22,
                "num_lab_procedures": 45,
                "discharge_disposition_id": 1,
                "admission_type_id": 1,
                "readmitted": "NO",
            }
        }
    }


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class Encounter(BaseModel):
    encounter_id: int
    patient_nbr: int
    age: str
    time_in_hospital: int
    number_inpatient: int
    number_emergency: int
    number_outpatient: int
    num_medications: int
    num_lab_procedures: int
    discharge_disposition_id: int
    admission_type_id: int
    readmitted: str
    risk_score: int
    risk_level: RiskLevel


class Intervention(BaseModel):
    intervention_id: int
    encounter_id: int
    status: Status
    assigned_to: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class HistoryEntry(BaseModel):
    old_status: Optional[str]
    new_status: str
    assigned_to: Optional[str]
    notes: Optional[str]
    changed_at: datetime


class EncounterDetail(Encounter):
    risk_reasons: List[str]
    intervention: Optional[Intervention]
    intervention_history: List[HistoryEntry]


class EncounterCreated(Encounter):
    """Response for POST /encounters."""
    risk_reasons: List[str]
    added_to_care_queue: bool
    queue_message: str


class EncounterPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[Encounter]


class PatientSearchResult(BaseModel):
    """Response for GET /patients/search.

    `items` is empty when nothing matches (the UI shows "No match").
    When more than one encounter matches, all of them are listed.
    """
    total: int
    limit: int
    offset: int
    filters: dict
    items: List[Encounter]

    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 1,
                "limit": 100,
                "offset": 0,
                "filters": {"patient_nbr": 888000001, "risk_score": None, "risk_level": "HIGH"},
                "items": [
                    {
                        "encounter_id": 999000001,
                        "patient_nbr": 888000001,
                        "age": "[60-70)",
                        "time_in_hospital": 8,
                        "number_inpatient": 4,
                        "number_emergency": 2,
                        "number_outpatient": 0,
                        "num_medications": 22,
                        "num_lab_procedures": 45,
                        "discharge_disposition_id": 1,
                        "admission_type_id": 1,
                        "readmitted": "NO",
                        "risk_score": 7,
                        "risk_level": "HIGH",
                    }
                ],
            }
        }
    }


class QueueItem(BaseModel):
    encounter_id: int
    patient_nbr: int
    age: str
    risk_score: int
    risk_level: RiskLevel
    risk_reasons: List[str]
    status: Status
    assigned_to: Optional[str]
    notes: Optional[str]
    updated_at: datetime


class QueuePage(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[QueueItem]


class OperationsSummary(BaseModel):
    total_encounters: int
    high_risk: int
    medium_risk: int
    low_risk: int
    queue_size: int
    excluded_not_contactable: int
    pending_interventions: int
    in_progress_interventions: int
    completed_interventions: int
    by_status: dict


class RiskGroupResult(BaseModel):
    risk_level: RiskLevel
    encounters: int
    readmitted_under_30_days: int
    readmission_rate: float
    lift_vs_baseline: float


class ReadmissionAnalysis(BaseModel):
    total_encounters: int
    total_readmitted_under_30_days: int
    baseline_readmission_rate: float
    high_risk_patients: int
    high_risk_readmitted_under_30_days: int
    high_risk_readmission_rate: float
    by_risk_level: List[RiskGroupResult]
    queue_encounters: int
    queue_readmitted_under_30_days: int
    queue_readmission_rate: float
    queue_share_of_all_encounters: float
    queue_capture_rate: float


class ManagementDashboard(BaseModel):
    total_encounters: int
    queue_size: int
    queue_share_of_all_encounters: float
    open_interventions: int
    completed_interventions: int
    completion_rate: float
    baseline_readmission_rate: float
    high_risk_readmission_rate: float
    high_risk_lift_vs_baseline: float
    queue_readmission_rate: float
    queue_capture_rate: float
    headline: str
    disclaimer: str
