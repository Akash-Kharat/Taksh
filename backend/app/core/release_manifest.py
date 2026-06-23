"""
Taksh Release Manifest — MS-20

Loads and exposes the release_manifest.json file for the release endpoint.
The manifest is cached on first access to avoid repeated filesystem reads.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("release_manifest")

# Resolve path relative to this file (backend/app/core/ → backend/)
_MANIFEST_PATH = Path(__file__).parent.parent.parent / "release_manifest.json"

MANIFEST_VERSION = "1.0.0"

_manifest_cache: Optional[Dict[str, Any]] = None


def load_manifest() -> Dict[str, Any]:
    """Read and cache release_manifest.json. Raises if file is missing or malformed."""
    global _manifest_cache
    if _manifest_cache is not None:
        return _manifest_cache

    try:
        raw = _MANIFEST_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        _manifest_cache = data
        logger.info(
            f"[release_manifest] Loaded manifest: "
            f"version={data.get('version')} from {_MANIFEST_PATH}"
        )
        return data
    except FileNotFoundError:
        logger.error(f"[release_manifest] release_manifest.json not found at {_MANIFEST_PATH}")
        raise
    except json.JSONDecodeError as exc:
        logger.error(f"[release_manifest] Malformed release_manifest.json: {exc}")
        raise


def get_manifest() -> Dict[str, Any]:
    """Returns the cached manifest, loading it if necessary."""
    return load_manifest()


def clear_cache() -> None:
    """Clears the manifest cache (used in tests)."""
    global _manifest_cache
    _manifest_cache = None
