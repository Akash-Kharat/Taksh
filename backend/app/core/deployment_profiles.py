"""
Taksh Deployment Profiles — MS-20

Defines three deployment presets that apply opinionated defaults at startup.
The active profile is selected via the TAKSH_PROFILE environment variable
(default: "development").

Profiles do not replace .env configuration — they apply layered defaults
that can still be overridden by explicit environment variables.
"""
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger("deployment_profiles")


class DeploymentProfile(str, Enum):
    DEVELOPMENT = "development"
    LAB         = "lab"
    PRODUCTION  = "production"


@dataclass(frozen=True)
class ProfileSettings:
    """Immutable preset overrides for a deployment profile."""
    name:                     str
    description:              str
    mock_providers:           bool
    log_level:                str
    strict_validation:        bool
    backup_enabled:           bool
    provider_health_required: bool
    enable_debug_reload:      bool


# ---------------------------------------------------------------------------
# Profile definitions
# ---------------------------------------------------------------------------

PROFILES: dict[DeploymentProfile, ProfileSettings] = {
    DeploymentProfile.DEVELOPMENT: ProfileSettings(
        name                     = "development",
        description              = "Local development with mock providers and debug logging",
        mock_providers           = True,
        log_level                = "DEBUG",
        strict_validation        = False,
        backup_enabled           = False,
        provider_health_required = False,
        enable_debug_reload      = True,
    ),
    DeploymentProfile.LAB: ProfileSettings(
        name                     = "lab",
        description              = "Internal lab with live Gemini, voice enabled, SQLite",
        mock_providers           = False,
        log_level                = "INFO",
        strict_validation        = False,
        backup_enabled           = False,
        provider_health_required = True,
        enable_debug_reload      = False,
    ),
    DeploymentProfile.PRODUCTION: ProfileSettings(
        name                     = "production",
        description              = "Production deployment — minimal logging, strict validation, backups required",
        mock_providers           = False,
        log_level                = "WARNING",
        strict_validation        = True,
        backup_enabled           = True,
        provider_health_required = True,
        enable_debug_reload      = False,
    ),
}


def get_active_profile() -> DeploymentProfile:
    """
    Returns the active deployment profile from settings.
    Falls back to DEVELOPMENT if the value is unrecognised.
    """
    from app.core.config import settings
    raw = settings.TAKSH_PROFILE.lower().strip()
    try:
        return DeploymentProfile(raw)
    except ValueError:
        logger.warning(
            f"[profile] Unknown TAKSH_PROFILE='{raw}'. "
            f"Valid values: {[p.value for p in DeploymentProfile]}. "
            "Defaulting to 'development'."
        )
        return DeploymentProfile.DEVELOPMENT


def get_profile_settings(profile: Optional[DeploymentProfile] = None) -> ProfileSettings:
    """Returns the ProfileSettings for the given profile (or the active one)."""
    if profile is None:
        profile = get_active_profile()
    return PROFILES[profile]


def apply_profile(profile: Optional[DeploymentProfile] = None) -> ProfileSettings:
    """
    Applies the profile's defaults to the global Settings instance.

    Only overrides settings that have not been explicitly customised via
    environment variables (i.e. still at their pydantic default values).
    Returns the applied ProfileSettings.
    """
    from app.core.config import settings

    if profile is None:
        profile = get_active_profile()

    ps = PROFILES[profile]

    # Apply log level if at default
    if settings.LOG_LEVEL == "INFO" and ps.log_level != "INFO":
        settings.LOG_LEVEL = ps.log_level

    # Apply mock provider defaults if at defaults
    if ps.mock_providers:
        if settings.DEFAULT_LLM_PROVIDER == "mock":
            pass  # already mock
        # In development, force mock if Gemini key is absent
        from app.core.config import settings as s
        if not s.GEMINI_API_KEY:
            settings.DEFAULT_LLM_PROVIDER  = "mock"
            settings.DEFAULT_STT_PROVIDER  = "mock"
            settings.DEFAULT_TTS_PROVIDER  = "mock"

    # Enable provider health checks for lab/production
    if ps.provider_health_required:
        settings.ENABLE_PROVIDER_HEALTH_CHECKS = True

    logger.info(
        f"[profile] Active profile: '{ps.name}' — {ps.description}"
    )
    return ps


# Module-level singleton for the active profile settings (set at startup)
_active_profile_settings: Optional[ProfileSettings] = None


def load_active_profile() -> ProfileSettings:
    """
    Called once during lifespan. Applies and caches the active profile.
    """
    global _active_profile_settings
    _active_profile_settings = apply_profile()
    return _active_profile_settings


def get_loaded_profile() -> Optional[ProfileSettings]:
    """Returns the cached profile settings (after load_active_profile() has run)."""
    return _active_profile_settings
