from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from services.tagging import get_tagging_rule_service


router = APIRouter(prefix="/tagging", tags=["tagging"])


class TagDefinitionListResponse(BaseModel):
    definitions: list[dict[str, Any]]
    total: int


class RuleVersionListResponse(BaseModel):
    versions: list[dict[str, Any]]
    total: int


class RuleVersionDetailResponse(BaseModel):
    version: dict[str, Any]


@router.get("/definitions", response_model=TagDefinitionListResponse)
def list_tag_definitions(
    request: Request,
    include_inactive: bool = Query(False, description="Include inactive definitions"),
) -> TagDefinitionListResponse:
    """List all tag definitions."""
    service = get_tagging_rule_service()
    definitions = service.list_tag_definitions(include_inactive=include_inactive)

    return TagDefinitionListResponse(
        definitions=definitions,
        total=len(definitions),
    )


@router.get("/versions", response_model=RuleVersionListResponse)
def list_rule_versions(
    request: Request,
    limit: int = Query(50, ge=1, le=100, description="Max versions to return"),
) -> RuleVersionListResponse:
    """List rule versions."""
    service = get_tagging_rule_service()
    versions = service.list_rule_versions(limit=limit)

    return RuleVersionListResponse(
        versions=versions,
        total=len(versions),
    )


@router.get("/versions/active", response_model=RuleVersionDetailResponse)
def get_active_rule_version(
    request: Request,
) -> RuleVersionDetailResponse:
    """Get the currently active rule version."""
    service = get_tagging_rule_service()
    version = service.get_active_rule_version()

    if not version:
        raise HTTPException(status_code=404, detail="No active rule version found")

    return RuleVersionDetailResponse(version=version)


@router.get("/versions/{version_code}", response_model=RuleVersionDetailResponse)
def get_rule_version(
    request: Request,
    version_code: str,
) -> RuleVersionDetailResponse:
    """Get a specific rule version by code."""
    service = get_tagging_rule_service()
    version = service.get_rule_version(version_code)

    if not version:
        raise HTTPException(status_code=404, detail=f"Rule version {version_code} not found")

    return RuleVersionDetailResponse(version=version)
