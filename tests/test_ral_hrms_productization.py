import json
from pathlib import Path

from glue.ral_hrms_productization import (
    BAHRAIN_LAW_PACK,
    RAL_DOCTYPES,
    RAL_HRMS_APP,
    RAL_ROLES,
    RAL_WORKSPACES,
    Ownership,
    ral_role_fixtures,
    ral_workspace_fixtures,
    validate_ral_productization_contract,
)


FIXTURE_DIR = (
    Path(__file__).resolve().parents[1]
    / "integrations"
    / "ral_hrms"
    / "ral_hrms"
    / "ral_hrms"
    / "fixtures"
)


def test_RAL_HRMS_APP_is_vendor_owned_and_branded() -> None:
    assert RAL_HRMS_APP.app_name == "ral_hrms"
    assert RAL_HRMS_APP.app_title == "RAL HRMS"
    assert RAL_HRMS_APP.app_publisher == "RAL Technologies"
    assert "RAL HRMS" in RAL_HRMS_APP.app_description


def test_ral_productization_contract_has_no_violations() -> None:
    assert validate_ral_productization_contract() == []


def test_all_ral_doctypes_are_tenant_scoped_and_ral_owned() -> None:
    assert RAL_DOCTYPES
    for doctype in RAL_DOCTYPES:
        assert doctype.name.startswith("RAL ")
        assert doctype.owner is Ownership.RAL
        assert doctype.tenant_required is True
        assert doctype.may_mutate_source_hr is False


def test_roles_map_to_openfga_relations_without_global_access() -> None:
    role_by_name = {role.name: role for role in RAL_ROLES}

    assert role_by_name["RAL Employee"].openfga_relation == "employee"
    assert role_by_name["RAL Manager"].openfga_relation == "manager"
    assert role_by_name["RAL HR Admin"].openfga_relation == "hr_admin"
    assert role_by_name["RAL Tenant Admin"].openfga_relation == "system_admin"

    for role in RAL_ROLES:
        assert role.tenant_scoped is True


def test_bahrain_law_pack_is_deterministic_and_source_verified() -> None:
    assert BAHRAIN_LAW_PACK.country_code == "BH"
    assert BAHRAIN_LAW_PACK.first_supported is True
    assert BAHRAIN_LAW_PACK.rules_are_deterministic is True
    assert BAHRAIN_LAW_PACK.official_source_required is True
    assert BAHRAIN_LAW_PACK.llm_may_compute is False
    assert "WPS export schema and validation" in BAHRAIN_LAW_PACK.planned_rule_families


def test_workspaces_reference_existing_ral_roles() -> None:
    role_names = {role.name for role in RAL_ROLES}
    assert RAL_WORKSPACES

    for workspace in RAL_WORKSPACES:
        assert workspace.name.startswith("RAL ")
        assert set(workspace.required_roles) <= role_names


def test_checked_in_role_fixture_matches_productization_contract() -> None:
    checked_in = json.loads((FIXTURE_DIR / "role.json").read_text(encoding="utf-8"))

    assert checked_in == ral_role_fixtures()


def test_checked_in_workspace_fixture_matches_productization_contract() -> None:
    checked_in = json.loads((FIXTURE_DIR / "workspace.json").read_text(encoding="utf-8"))

    assert checked_in == ral_workspace_fixtures()
