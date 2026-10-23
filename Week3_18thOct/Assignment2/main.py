# main.py
# FastAPI routes: request/response handling only.
# Each route calls service.py and turns service errors into HTTP errors.
#
# Run:  uvicorn main:app --reload
# Docs: http://127.0.0.1:8000/docs

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import service
from models import (
    EncounterCreate,
    EncounterCreated,
    EncounterDetail,
    EncounterPage,
    HighRiskPage,
    Intervention,
    InterventionStatus,
    InterventionUpdate,
    ManagementDashboard,
    OperationsSummary,
    PatientSearchResult,
    QueuePage,
    ReadmissionAnalysis,
    RiskLevel,
    Status,
)

app = FastAPI(
    title="Diabetes Readmission Intervention Queue",
    description=(
        "Learning prototype for the Testleaf FDE program. "
        "NOT a clinically validated scoring system - not for real patient care decisions."
    ),
    version="1.0.0",
)

# CORS: lets a web page running on another address (e.g. a React app on
# http://localhost:5173) call this API from the browser.
# "*" = allow everyone. Fine for local development; restrict it in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    # Browsers hide most response headers from JavaScript on other origins.
    # expose_headers lets the front end read our X-Backend header.
    expose_headers=["X-Backend"],
)


@app.middleware("http")
async def add_backend_header(request, call_next):
    """Stamp every response so a client can confirm it came from this Python API."""
    response = await call_next(request)
    response.headers["X-Backend"] = "Python FastAPI"
    return response


@app.get("/", tags=["Health"])
def root():
    return {"message": "Diabetes Readmission Intervention Queue API. See /docs"}


# ---------------------------------------------------------------------------
# Encounters
# ---------------------------------------------------------------------------

@app.get("/encounters", response_model=EncounterPage, tags=["Encounters"])
def list_encounters(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    risk_level: Optional[RiskLevel] = None,
):
    return service.list_encounters(limit, offset, risk_level)


@app.post("/encounters", response_model=EncounterCreated, status_code=201, tags=["Encounters"])
def create_encounter(encounter: EncounterCreate):
    """Add one new encounter. Risk is calculated by the service, not sent by the client."""
    try:
        return service.create_encounter(encounter.model_dump())
    except service.ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@app.get("/encounters/{encounter_id}", response_model=EncounterDetail, tags=["Encounters"])
def get_encounter(encounter_id: int):
    try:
        return service.get_encounter(encounter_id)
    except service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Patient search
# ---------------------------------------------------------------------------

@app.get("/patients/search", response_model=PatientSearchResult, tags=["Patients"])
def search_patients(
    patient_nbr: Optional[int] = Query(None, gt=0, description="Patient number (exact match)"),
    risk_score: Optional[int] = Query(None, ge=0, le=8, description="Risk score 0-8 (exact match)"),
    risk_level: Optional[RiskLevel] = Query(None, description="LOW, MEDIUM or HIGH"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Search by patient number and/or risk score and/or risk level.

    - Any combination of the three filters (at least one is required).
    - No match -> 200 with `total: 0` and `items: []`.
    - Several matches -> all of them are listed.
    """
    try:
        return service.search_patients(patient_nbr, risk_score, risk_level, limit, offset)
    except service.BadRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/patients/high-risk", response_model=HighRiskPage, tags=["Patients"])
def list_high_risk_patients(
    patient_nbr: Optional[int] = Query(None, gt=0, description="Optional: one patient only"),
    status: Optional[Status] = Query(None, description="Optional: intervention status"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """HIGH-risk encounters with their care-intervention status, highest score first."""
    try:
        return service.list_high_risk_patients(patient_nbr, status, limit, offset)
    except service.BadRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get(
    "/encounters/{encounter_id}/intervention-status",
    response_model=InterventionStatus,
    tags=["Interventions"],
)
def get_intervention_status(encounter_id: int):
    """Current care-intervention status and history for one encounter."""
    try:
        return service.get_intervention_status(encounter_id)
    except service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Care queue
# ---------------------------------------------------------------------------

@app.get("/care-queue", response_model=QueuePage, tags=["Care Queue"])
def get_care_queue(
    min_score: Optional[int] = Query(None, ge=0, le=8),
    status: Optional[Status] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """MEDIUM + HIGH risk encounters, highest score first."""
    try:
        return service.get_care_queue(["MEDIUM", "HIGH"], min_score, status, limit, offset)
    except service.BadRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/care-queue/high", response_model=QueuePage, tags=["Care Queue"])
def get_high_risk_queue(
    status: Optional[Status] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """HIGH risk encounters only."""
    try:
        return service.get_care_queue(["HIGH"], None, status, limit, offset)
    except service.BadRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Interventions
# ---------------------------------------------------------------------------

@app.patch("/interventions/{encounter_id}", response_model=Intervention, tags=["Interventions"])
def update_intervention(encounter_id: int, update: InterventionUpdate):
    try:
        return service.update_intervention(
            encounter_id, update.status, update.assigned_to, update.notes
        )
    except service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except service.BadRequestError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@app.get("/operations/summary", response_model=OperationsSummary, tags=["Metrics"])
def operations_summary():
    return service.get_operations_summary()


@app.get("/operations/readmission-analysis", response_model=ReadmissionAnalysis, tags=["Metrics"])
def readmission_analysis():
    return service.get_readmission_analysis()


@app.get("/management/dashboard", response_model=ManagementDashboard, tags=["Metrics"])
def management_dashboard():
    return service.get_management_dashboard()
