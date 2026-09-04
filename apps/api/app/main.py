from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl


class TargetType(str, Enum):
    chatbot = "chatbot"
    rag = "rag"
    agent = "agent"
    custom_api = "custom_api"


class AuthorizationScope(BaseModel):
    signed_by: str = Field(min_length=1)
    allowed_hostnames: list[str] = Field(min_length=1)
    approved_categories: list[str] = Field(min_length=1)
    max_requests: int = Field(gt=0, le=10_000)
    max_concurrency: int = Field(gt=0, le=20)
    emergency_stop_contact: str = Field(min_length=1)
    expires_at: datetime


class TargetRegistration(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    target_type: TargetType
    base_url: HttpUrl
    environment: Literal["development", "staging", "production"]


class ScanRequest(BaseModel):
    target: TargetRegistration
    authorization: AuthorizationScope
    categories: list[str] = Field(min_length=1)
    safe_test_mode: bool = True


class Finding(BaseModel):
    id: str
    title: str
    category: str
    severity: Literal["critical", "high", "medium", "low", "informational"]
    status: Literal["open", "mitigated"] = "open"
    evidence_status: str
    reproducibility: float = Field(ge=0, le=1)


class ScanRecord(BaseModel):
    scan_id: str
    status: Literal["queued", "running", "completed", "failed"]
    target_name: str
    target_type: TargetType
    categories: list[str]
    tests_run: int
    findings: list[Finding]
    created_at: datetime


app = FastAPI(
    title="Vulnora API",
    version="0.1.0",
    description="Authorization-first orchestration API for LLM security assessments.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

scans: dict[str, ScanRecord] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/scans", status_code=202)
def create_scan(request: ScanRequest) -> dict[str, str]:
    expires_at = request.authorization.expires_at
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        raise HTTPException(status_code=400, detail="Authorization expiry must include a timezone")

    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Authorization scope has expired")

    if request.target.base_url.host not in request.authorization.allowed_hostnames:
        raise HTTPException(status_code=400, detail="Target hostname is outside the authorization scope")

    if not set(request.categories).issubset(set(request.authorization.approved_categories)):
        raise HTTPException(
            status_code=400,
            detail="Requested categories exceed the approved authorization scope",
        )

    scan_id = f"scan_{uuid4().hex[:12]}"
    findings = [
        Finding(
            id="F-001",
            title="Retrieved context can override system intent",
            category="Prompt injection",
            severity="critical",
            evidence_status="Reproducible in controlled demo fixture",
            reproducibility=0.8,
        ),
        Finding(
            id="F-002",
            title="Sensitive source metadata appears in responses",
            category="Sensitive information disclosure",
            severity="high",
            evidence_status="Sanitized evidence captured",
            reproducibility=0.6,
        ),
        Finding(
            id="F-003",
            title="Tool permissions exceed the declared scope",
            category="Excessive agency",
            severity="medium",
            evidence_status="Requires manual permission review",
            reproducibility=0.4,
        ),
    ]
    record = ScanRecord(
        scan_id=scan_id,
        status="completed",
        target_name=request.target.name,
        target_type=request.target.target_type,
        categories=request.categories,
        tests_run=min(request.authorization.max_requests, 18),
        findings=findings,
        created_at=datetime.now(timezone.utc),
    )
    scans[scan_id] = record
    return {"scan_id": scan_id, "status": record.status, "message": "Scan completed in demo mode"}


@app.get("/api/v1/scans/{scan_id}", response_model=ScanRecord)
def get_scan(scan_id: str) -> ScanRecord:
    record = scans.get(scan_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return record


@app.get("/api/v1/scans", response_model=list[ScanRecord])
def list_scans() -> list[ScanRecord]:
    return list(scans.values())
