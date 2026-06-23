# ADR-021: Taksh Version 1.0 Freeze & Release

## Status
Accepted

## Context
As we reach Milestone-21, Taksh is declared production-ready. To guarantee stability in production environments, ensure reliable deployment, and establish a clear maintenance baseline, we require a complete feature freeze and version pinning.

We need to guarantee that:
1. Deployed code matches the frozen release manifest exactly.
2. The runtime cleans up all socket, provider, and SQLite database resources properly on shutdown to prevent resource locking on Windows hosts (`WinError 32`).
3. Database migrations match the expected head revision exactly to prevent drift.

## Decisions
1. **Feature Freeze**: No new AI capabilities, runtime features, API contracts, database schemas, or provider interfaces will be modified. Only bug fixes, warning elimination, and resource cleanup are permitted.
2. **Release Manifest Immutability**: Pin the version to `1.0.0` in `release_manifest.json` and validate against `app/core/release_manifest.py` `MANIFEST_VERSION = "1.0.0"` on startup.
3. **Database Migration Strictness**: Fail startup if there is any migration drift (`current_revision != head_revision`).
4. **Shutdown Resource Cleanup**: Verify that all open WebSockets, audio providers, ChromaDB clients, and active runtime/voice sessions are explicitly closed and evicted from memory when the FastAPI application shuts down.
5. **Git Branching Policy**: Maintain a dedicated `release/v1.0` branch for future `v1.0.x` bug fixes, and tag the release as `v1.0.0`.

## Consequences
- The system is guaranteed to boot cleanly and only if database schema and manifest versions are fully aligned.
- Accidental changes to the release version or missing database migrations will be caught immediately at startup.
- Shutdown is clean and will not produce WinError 32 file locking errors on Windows hosts.
- Future hotfixes for version 1.0.x can be easily targeted at the `release/v1.0` branch.
