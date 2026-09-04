from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


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
    environment: Literal["development", "staging", "production"] = "development"


class ScanRequest(BaseModel):
    target: TargetRegistration
    authorization: AuthorizationScope
    categories: list[str] = Field(min_length=1)
    safe_test_mode: bool = True


class Finding(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    test_id: Optional[str] = None
    title: str
    category: str
    severity: Literal["critical", "high", "medium", "low", "informational"]
    status: Literal["open", "mitigated"] = "open"
    evidence_status: str
    reproducibility: float = Field(ge=0, le=1)
    raw_prompt: Optional[str] = None
    raw_response: Optional[str] = None
    mitigation: Optional[str] = None
    created_at: Optional[datetime] = None


class ScanRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: str
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    target_name: str
    target_type: TargetType
    categories: list[str]
    tests_run: int
    findings: list[Finding]
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class CatalogTestCaseInfo(BaseModel):
    id: str
    name: str
    category: str
    severity: str
    description: str
    remediation: str
