import os
from pathlib import Path
from typing import Any, List, Optional
import yaml
from pydantic import BaseModel, Field


class EvaluationRule(BaseModel):
    type: str  # "regex_match", "contains"
    patterns: List[str]


class SecurityTestCase(BaseModel):
    id: str
    name: str
    category: str
    display_category: str
    severity: str
    description: str
    payloads: List[str]
    evaluation_rules: EvaluationRule
    remediation: str


class TestCatalog(BaseModel):
    version: str
    title: str
    description: str
    test_cases: List[SecurityTestCase]


def get_catalog_path() -> Path:
    # Look for test_catalog directory relative to project root or current working dir
    # apps/api/app/catalog.py -> parents[3] is project root (c:\projects\p_1)
    current_file = Path(__file__).resolve()
    candidates = [
        current_file.parents[3] / "test_catalog" / "owasp_llm_v1.yaml",
        current_file.parents[2] / "test_catalog" / "owasp_llm_v1.yaml",
        Path("test_catalog") / "owasp_llm_v1.yaml",
        Path("..") / "test_catalog" / "owasp_llm_v1.yaml",
        Path("../..") / "test_catalog" / "owasp_llm_v1.yaml",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("Could not find owasp_llm_v1.yaml in test_catalog directory")


def load_catalog() -> TestCatalog:
    path = get_catalog_path()
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return TestCatalog.model_validate(data)


def get_test_cases_for_categories(categories: List[str]) -> List[SecurityTestCase]:
    catalog = load_catalog()
    norm_categories = {c.lower().replace(" ", "_").replace("-", "_") for c in categories}
    selected = []
    for tc in catalog.test_cases:
        cat_norm = tc.category.lower().replace(" ", "_").replace("-", "_")
        if cat_norm in norm_categories or "all" in norm_categories:
            selected.append(tc)
    return selected
