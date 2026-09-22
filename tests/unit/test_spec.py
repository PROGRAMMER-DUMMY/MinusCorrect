"""
Unit tests for MinusCorrect spec scaffolding and design engine.
"""

from pathlib import Path
import pytest
from minuscorrect.spec import (
    generate_prd,
    generate_trd,
    generate_refero_design,
    generate_appflow,
    generate_schema,
    generate_plan,
    scaffold_spec_suite,
)


def test_generate_prd() -> None:
    prd = generate_prd("TestApp", "A test application for multi-tenant analytics.")
    assert "# Product Requirements Document (PRD)" in prd
    assert "TestApp" in prd
    assert "User Personas & Permissions Matrix" in prd
    assert "Non-Functional Requirements & SLAs" in prd
    assert "RTO" in prd
    assert "RPO" in prd


def test_generate_trd() -> None:
    trd = generate_trd("TestApp", "Technical specifications.")
    assert "# Technical Requirements Document (TRD)" in trd
    assert "Next.js 15" in trd
    assert "PostgreSQL 16" in trd
    assert "Supabase" in trd
    assert "ENABLE ROW LEVEL SECURITY" in trd


def test_generate_refero_design() -> None:
    design = generate_refero_design("TestApp")
    assert "Design System" in design or "Refero" in design
    assert "@theme" in design
    assert "--color-brand-primary" in design
    assert "Double-Submit" in design
    assert "focus trap" in design.lower() or "Focus Trap" in design or "Modal" in design
    assert "styles.refero.design" in design
    assert "mobbin.com" in design
    assert "saaspo.com" in design
    assert "pageflows.com" in design
    assert "godly.website" in design
    assert "land-book.com" in design
    assert "Dribbble" in design


def test_generate_appflow() -> None:
    appflow = generate_appflow("TestApp")
    assert "Application Flow" in appflow or "State Machine" in appflow
    assert "```mermaid" in appflow
    assert "Unauthenticated" in appflow or "AuthSessionCheck" in appflow


def test_generate_schema() -> None:
    schema = generate_schema("TestApp")
    assert "ENABLE ROW LEVEL SECURITY" in schema
    assert "CREATE TABLE public.tenants" in schema
    assert "CREATE TABLE public.tenant_members" in schema
    assert "CREATE TABLE public.projects" in schema
    assert "CREATE TABLE public.processed_webhooks" in schema
    assert "CREATE TABLE public.audit_logs" in schema
    assert "idx_tenant_members_tenant_id" in schema
    assert "idx_audit_logs_actor_id" in schema


def test_generate_plan() -> None:
    plan = generate_plan("TestApp", "Analytics platform")
    assert "Architectural Spec" in plan or "Ticket" in plan


def test_scaffold_spec_suite(tmp_path: Path) -> None:
    specs = scaffold_spec_suite(output_dir=tmp_path, project_name="MatrixCorp", description="High-throughput engine")
    assert len(specs) == 6
    expected_files = {"PRD.md", "TRD.md", "DESIGN.md", "APPFLOW.md", "SCHEMA.sql", "PLAN.md"}
    assert set(specs.keys()) == expected_files

    for name, p in specs.items():
        assert p.exists()
        assert p.is_file()
        content = p.read_text(encoding="utf-8")
        assert len(content) > 100
        assert "MatrixCorp" in content or name == "PLAN.md"
