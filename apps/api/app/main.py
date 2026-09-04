import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import List
from uuid import uuid4

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from apps.api.app.catalog import load_catalog
from apps.api.app.database import SessionLocal, get_db, init_db
from apps.api.app.models import (
    AuthorizationScopeModel,
    FindingModel,
    ScanModel,
    TargetModel,
    utc_now,
)
from apps.api.app.schemas import (
    CatalogTestCaseInfo,
    Finding,
    ScanRecord,
    ScanRequest,
)
from workers.executor import execute_scan_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Vulnora API",
    version="0.2.0",
    description="Authorization-first orchestration API for LLM security assessments with persistent models and isolated workers.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/catalog", response_model=List[CatalogTestCaseInfo])
def get_catalog_tests():
    try:
        catalog = load_catalog()
        return [
            CatalogTestCaseInfo(
                id=tc.id,
                name=tc.name,
                category=tc.category,
                severity=tc.severity,
                description=tc.description,
                remediation=tc.remediation,
            )
            for tc in catalog.test_cases
        ]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load catalog: {exc}")


@app.post("/api/v1/scans", status_code=status.HTTP_202_ACCEPTED)
async def create_scan(request: ScanRequest, db: Session = Depends(get_db)):
    expires_at = request.authorization.expires_at
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        raise HTTPException(status_code=400, detail="Authorization expiry must include a timezone")

    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Authorization scope has expired")

    host = request.target.base_url.host
    if host not in request.authorization.allowed_hostnames and "localhost" not in request.authorization.allowed_hostnames:
        raise HTTPException(status_code=400, detail="Target hostname is outside the authorization scope")

    if not set(request.categories).issubset(set(request.authorization.approved_categories)):
        raise HTTPException(
            status_code=400,
            detail="Requested categories exceed the approved authorization scope",
        )

    target_id = f"target_{uuid4().hex[:10]}"
    db_target = TargetModel(
        id=target_id,
        name=request.target.name,
        target_type=request.target.target_type.value,
        base_url=str(request.target.base_url),
        environment=request.target.environment,
    )
    db.add(db_target)

    auth_id = f"auth_{uuid4().hex[:10]}"
    db_auth = AuthorizationScopeModel(
        id=auth_id,
        signed_by=request.authorization.signed_by,
        allowed_hostnames=request.authorization.allowed_hostnames,
        approved_categories=request.authorization.approved_categories,
        max_requests=request.authorization.max_requests,
        max_concurrency=request.authorization.max_concurrency,
        emergency_stop_contact=request.authorization.emergency_stop_contact,
        expires_at=request.authorization.expires_at,
    )
    db.add(db_auth)

    scan_id = f"scan_{uuid4().hex[:12]}"
    db_scan = ScanModel(
        id=scan_id,
        target_id=target_id,
        authorization_id=auth_id,
        target_name=request.target.name,
        target_type=request.target.target_type.value,
        status="queued",
        categories=request.categories,
        safe_test_mode=request.safe_test_mode,
        tests_run=0,
        created_at=utc_now(),
    )
    db.add(db_scan)
    db.commit()

    # Launch background worker execution task
    asyncio.create_task(execute_scan_task(scan_id, SessionLocal))

    return {
        "scan_id": scan_id,
        "status": "queued",
        "message": "Scan queued for execution by security worker",
    }


def scan_model_to_record(scan: ScanModel) -> ScanRecord:
    findings = [
        Finding(
            id=f.id,
            test_id=f.test_id,
            title=f.title,
            category=f.category,
            severity=f.severity,  # type: ignore
            status=f.status,  # type: ignore
            evidence_status=f.evidence_status,
            reproducibility=f.reproducibility,
            raw_prompt=f.raw_prompt,
            raw_response=f.raw_response,
            mitigation=f.mitigation,
            created_at=f.created_at,
        )
        for f in scan.findings
    ]
    return ScanRecord(
        scan_id=scan.id,
        status=scan.status,  # type: ignore
        target_name=scan.target_name,
        target_type=scan.target_type,  # type: ignore
        categories=scan.categories or [],
        tests_run=scan.tests_run or 0,
        findings=findings,
        created_at=scan.created_at,
        completed_at=scan.completed_at,
        error_message=scan.error_message,
    )


@app.get("/api/v1/scans/{scan_id}", response_model=ScanRecord)
def get_scan(scan_id: str, db: Session = Depends(get_db)) -> ScanRecord:
    scan = db.query(ScanModel).filter(ScanModel.id == scan_id).first()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan_model_to_record(scan)


@app.get("/api/v1/scans", response_model=List[ScanRecord])
def list_scans(db: Session = Depends(get_db)) -> List[ScanRecord]:
    scans = db.query(ScanModel).order_by(ScanModel.created_at.desc()).all()
    return [scan_model_to_record(s) for s in scans]


@app.post("/api/v1/scans/{scan_id}/cancel")
def cancel_scan(scan_id: str, db: Session = Depends(get_db)):
    scan = db.query(ScanModel).filter(ScanModel.id == scan_id).first()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    if scan.status in ["completed", "failed", "cancelled"]:
        return {"status": scan.status, "message": f"Scan is already {scan.status}"}
    scan.status = "cancelled"
    db.commit()
    return {"status": "cancelled", "message": "Emergency cancellation triggered"}
