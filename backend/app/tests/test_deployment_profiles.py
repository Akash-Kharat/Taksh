"""
MS-20 Tests — Deployment Profiles
"""
import pytest
from unittest.mock import patch
from app.core.deployment_profiles import (
    DeploymentProfile,
    ProfileSettings,
    PROFILES,
    get_active_profile,
    get_profile_settings,
    load_active_profile,
    get_loaded_profile,
    apply_profile,
)
import app.core.deployment_profiles as dp_module



def test_all_three_profiles_exist():
    assert DeploymentProfile.DEVELOPMENT in PROFILES
    assert DeploymentProfile.LAB in PROFILES
    assert DeploymentProfile.PRODUCTION in PROFILES


def test_profile_settings_are_frozen():
    ps = PROFILES[DeploymentProfile.DEVELOPMENT]
    with pytest.raises((AttributeError, TypeError)):
        ps.name = "modified"  # type: ignore


def test_development_profile_uses_mock_providers():
    ps = PROFILES[DeploymentProfile.DEVELOPMENT]
    assert ps.mock_providers is True
    assert ps.log_level == "DEBUG"
    assert ps.strict_validation is False
    assert ps.backup_enabled is False
    assert ps.provider_health_required is False


def test_lab_profile_has_live_providers():
    ps = PROFILES[DeploymentProfile.LAB]
    assert ps.mock_providers is False
    assert ps.provider_health_required is True
    assert ps.log_level == "INFO"


def test_production_profile_is_strict():
    ps = PROFILES[DeploymentProfile.PRODUCTION]
    assert ps.mock_providers is False
    assert ps.strict_validation is True
    assert ps.backup_enabled is True
    assert ps.provider_health_required is True
    assert ps.log_level == "WARNING"


def test_get_active_profile_reads_settings():
    with patch("app.core.config.settings.TAKSH_PROFILE", "lab"):
        profile = get_active_profile()
    assert profile == DeploymentProfile.LAB


def test_get_active_profile_defaults_to_development_on_unknown():
    with patch("app.core.config.settings.TAKSH_PROFILE", "invalid_xyz"):
        profile = get_active_profile()
    assert profile == DeploymentProfile.DEVELOPMENT


def test_get_profile_settings_returns_correct_preset():
    ps = get_profile_settings(DeploymentProfile.PRODUCTION)
    assert ps.name == "production"


def test_get_profile_settings_uses_active_profile_when_none():
    with patch("app.core.config.settings.TAKSH_PROFILE", "development"):
        ps = get_profile_settings(None)
    assert ps.name == "development"


def test_load_active_profile_caches_result():
    with patch("app.core.config.settings.TAKSH_PROFILE", "development"):
        ps = load_active_profile()
    assert get_loaded_profile() is ps


def test_apply_profile_returns_profile_settings():
    with patch("app.core.config.settings.TAKSH_PROFILE", "development"):
        ps = apply_profile(DeploymentProfile.DEVELOPMENT)
    assert isinstance(ps, ProfileSettings)


def test_deployment_profile_enum_values():
    assert DeploymentProfile.DEVELOPMENT.value == "development"
    assert DeploymentProfile.LAB.value == "lab"
    assert DeploymentProfile.PRODUCTION.value == "production"
