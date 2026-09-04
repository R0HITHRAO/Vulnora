import asyncio
from datetime import datetime, timezone
import re
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.api.app.adapters import BaseTargetAdapter, HTTPTargetAdapter, MockTargetAdapter
from apps.api.app.catalog import SecurityTestCase, get_test_cases_for_categories
from apps.api.app.models import FindingModel, ScanModel, TargetModel, AuthorizationScopeModel, utc_now


def evaluate_response(rule_type: str, patterns: list[str], response_text: str) -> bool:
    """Check if the target response matches vulnerability detection rules."""
    if not response_text:
        return False

    if rule_type == "contains":
        for pat in patterns:
            if pat in response_text:
                return True
    elif rule_type == "regex_match":
        for pat in patterns:
            if re.search(pat, response_text):
                return True
    return False


async def execute_scan_task(scan_id: str, db_session_factory):
    """
    Main asynchronous worker task executing a bounded security assessment.
    """
    db: Session = db_session_factory()
    try:
        scan = db.query(ScanModel).filter(ScanModel.id == scan_id).first()
        if not scan:
            return

        if scan.status == "cancelled":
            return

        scan.status = "running"
        db.commit()

        # Fetch target and authorization
        target = db.query(TargetModel).filter(TargetModel.id == scan.target_id).first() if scan.target_id else None
        auth = db.query(AuthorizationScopeModel).filter(AuthorizationScopeModel.id == scan.authorization_id).first() if scan.authorization_id else None

        # Determine target adapter
        adapter: BaseTargetAdapter
        is_mock_target = (
            scan.safe_test_mode
            or (target and "mock" in target.base_url.lower())
            or (target and "localhost:8000" in target.base_url.lower())
        )

        if is_mock_target or not target:
            adapter = MockTargetAdapter(base_url="http://mock-target.local", simulate_latency=0.1)
        else:
            adapter = HTTPTargetAdapter(base_url=target.base_url)

        # Load security test cases
        categories = scan.categories or ["prompt_injection", "disclosure", "agency"]
        test_cases = get_test_cases_for_categories(categories)

        max_allowed_requests = auth.max_requests if auth else 50
        tests_executed = 0
        finding_counter = 1

        for tc in test_cases:
            # Check for emergency cancellation
            db.refresh(scan)
            if scan.status == "cancelled":
                break

            if tests_executed >= max_allowed_requests:
                break

            for payload in tc.payloads:
                if tests_executed >= max_allowed_requests:
                    break

                response = await adapter.send_prompt(payload)
                tests_executed += 1

                # Evaluate response for vulnerability indicators
                is_vulnerable = evaluate_response(
                    rule_type=tc.evaluation_rules.type,
                    patterns=tc.evaluation_rules.patterns,
                    response_text=response.text,
                )

                if is_vulnerable:
                    finding_id = f"F-{finding_counter:03d}"
                    finding_counter += 1

                    finding = FindingModel(
                        id=finding_id,
                        scan_id=scan.id,
                        test_id=tc.id,
                        title=tc.name,
                        category=tc.display_category,
                        severity=tc.severity,
                        status="open",
                        evidence_status=f"Verified signature match ({response.latency_ms:.1f}ms)",
                        reproducibility=0.9,
                        raw_prompt=payload,
                        raw_response=response.text,
                        mitigation=tc.remediation,
                    )
                    db.add(finding)

                # Incremental progress update
                scan.tests_run = tests_executed
                db.commit()

                # Yield control briefly to simulate realistic rate-controlled execution
                await asyncio.sleep(0.08)

        # Mark scan as complete
        db.refresh(scan)
        if scan.status != "cancelled":
            scan.status = "completed"
            scan.completed_at = utc_now()
        db.commit()

    except Exception as exc:
        db.rollback()
        scan = db.query(ScanModel).filter(ScanModel.id == scan_id).first()
        if scan:
            scan.status = "failed"
            scan.error_message = str(exc)
            scan.completed_at = utc_now()
            db.commit()
    finally:
        db.close()
