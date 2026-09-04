from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship

from .database import Base


def utc_now():
    return datetime.now(timezone.utc)


class TargetModel(Base):
    __tablename__ = "targets"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    target_type = Column(String(32), nullable=False)
    base_url = Column(String(512), nullable=False)
    environment = Column(String(32), nullable=False, default="development")
    created_at = Column(DateTime(timezone=True), default=utc_now)


class AuthorizationScopeModel(Base):
    __tablename__ = "authorizations"

    id = Column(String(64), primary_key=True, index=True)
    signed_by = Column(String(128), nullable=False)
    allowed_hostnames = Column(JSON, nullable=False, default=list)
    approved_categories = Column(JSON, nullable=False, default=list)
    max_requests = Column(Integer, nullable=False, default=100)
    max_concurrency = Column(Integer, nullable=False, default=2)
    emergency_stop_contact = Column(String(128), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class ScanModel(Base):
    __tablename__ = "scans"

    id = Column(String(64), primary_key=True, index=True)
    target_id = Column(String(64), ForeignKey("targets.id"), nullable=True)
    authorization_id = Column(String(64), ForeignKey("authorizations.id"), nullable=True)
    target_name = Column(String(128), nullable=False)
    target_type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="queued")  # queued, running, completed, failed, cancelled
    categories = Column(JSON, nullable=False, default=list)
    safe_test_mode = Column(Boolean, default=True)
    tests_run = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    findings = relationship("FindingModel", back_populates="scan", cascade="all, delete-orphan")


class FindingModel(Base):
    __tablename__ = "findings"

    id = Column(String(64), primary_key=True, index=True)
    scan_id = Column(String(64), ForeignKey("scans.id"), nullable=False, index=True)
    test_id = Column(String(64), nullable=True)
    title = Column(String(256), nullable=False)
    category = Column(String(128), nullable=False)
    severity = Column(String(32), nullable=False)  # critical, high, medium, low, informational
    status = Column(String(32), nullable=False, default="open")  # open, mitigated
    evidence_status = Column(String(256), nullable=False)
    reproducibility = Column(Float, nullable=False, default=1.0)
    raw_prompt = Column(Text, nullable=True)
    raw_response = Column(Text, nullable=True)
    mitigation = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)

    scan = relationship("ScanModel", back_populates="findings")
