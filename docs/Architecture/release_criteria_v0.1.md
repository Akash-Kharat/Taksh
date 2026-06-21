# Taksh v0.1 Release Criteria
*(System Validation Gateways and Pass/Fail Acceptance Conditions)*

> [!IMPORTANT]
> This document defines the quantitative gates and qualitative conditions that the **Taksh v0.1 MVP** must satisfy before it can be considered production-ready. These criteria are frozen alongside the system architecture.

---

## 1. Functional Criteria

| ID | Capability | Validation Scenario | PASS Condition | FAIL Condition |
| :--- | :--- | :--- | :--- | :--- |
| **FC-01** | Bidirectional Audio | Stream raw voice input to backend; receive raw voice response. | System establishes WebSocket tunnel, user speech is transcribed, and Gemini voice response plays back clearly. | WebSocket fails to connect; audio chunks are dropped; playback is distorted. |
| **FC-02** | Session Logging | Generate post-session logs and update database records. | Upon WS disconnect, SQLite database updates `session_logs` and writes a summary markdown file under `.taksh/memory/session_history/`. | SQLite fails to write; summary markdown is missing or empty on exit. |
| **FC-03** | Knowledge Ingestion | Scan and ingest local repository markdown files into vector store. | Scanning an index directory of 20 documents finishes without exceptions, and content is searchable. | Scanning crashes; vector index contains empty pages; search returns zero matches. |

---

## 2. Performance Criteria

| ID | Metric | Measurement Method | PASS Condition | FAIL Condition |
| :--- | :--- | :--- | :--- | :--- |
| **PC-01** | Response Latency | Network packet logger (VAD boundary to audio start). | Median response latency (p50) $\le 1.2$ seconds; p95 latency $\le 1.8$ seconds. | Median response latency (p50) $> 1.2$ seconds. |
| **PC-02** | UI Frame Rate | Chrome DevTools Performance Profiler during active streams. | Main UI thread retains $\ge 58$ FPS. Zero UI thread blockages $> 50$ms. | UI freezes during incoming audio streams; frame rate drops below 30 FPS. |
| **PC-03** | RAG Search Speed | Backend execution timer logs. | Hybrid query (vector lookup + FTS5 index) finishes in $\le 150$ms. | Combined query execution takes $> 250$ms. |

---

## 3. Memory Criteria

| ID | Vector | Validation Scenario | PASS Condition | FAIL Condition |
| :--- | :--- | :--- | :--- | :--- |
| **MC-01** | Tiered Isolation | Terminate session and check system RAM/state. | Volatile sensory memory (active cursor, selection) is completely purged from RAM. DB matches disk state. | Volatile telemetry leaks into the next session; database commits are corrupted. |
| **MC-02** | Core Identity Lock | Execute mock file-overwrite call to `core_identity.md`. | System singleton blocks write requests to `.taksh/identity/core_identity.md` with permission error. | Singleton allows writing to `core_identity.md` or fails to cache it securely. |

---

## 4. Voice Criteria

| ID | Capability | Validation Scenario | PASS Condition | FAIL Condition |
| :--- | :--- | :--- | :--- | :--- |
| **VC-01** | VAD Boundary Precision | Voice streaming during ambient noise (typing/breathing). | Silero VAD filters out keyboard typing and deep breaths, only streaming active voice chunks. | Background typing triggers false transmission; initial syllables of speech are truncated. |
| **VC-02** | Interruption Latency | Speak over assistant during active playback. | Playback stops, audio buffer is flushed, and Gemini cancellation is sent in $\le 200$ms. | Audio continues playing for $> 300$ms after user starts speaking. |

---

## 5. Skills Criteria

| ID | Requirement | Validation Scenario | PASS Condition | FAIL Condition |
| :--- | :--- | :--- | :--- | :--- |
| **SC-01** | Domain-Centric Naming | Audit Dashboard UI elements and active prompt payloads. | Dashboard UI and prompt logs display only domain-centric skill names (e.g., *Full-Stack Software Architect*). | Technical framework terms (e.g., *Django Architect*, *FreeRTOS Expert*) are exposed in the UI. |
| **SC-02** | Dynamic Activation | Change workspace file to target stack (e.g. Django model). | Telemetry update changes active skill state within 1 second. | Telemetry updates but active skill fails to switch, or activates unrelated skills. |

---

## 6. Security Criteria

| ID | Target | Technical Action | PASS Condition | FAIL Condition |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | Local Loopback Enforcement | Port scan/curl from external network interface. | FastAPI backend rejects all network queries not originating from `127.0.0.1`. | Backend accepts external TCP connections on port 8000. |
| **SEC-02** | Secret Leak Prevention | Scan database payload logs for regex patterns (API keys/credentials). | Automated scanner filters and masks database ingestion of `.env` files or credentials. | Database contains unmasked raw passwords, tokens, or private environment files. |

---

## 7. Documentation Criteria

| ID | Requirement | Validation Tool | PASS Condition | FAIL Condition |
| :--- | :--- | :--- | :--- | :--- |
| **DC-01** | Frontmatter Validation | CI/CD YAML Schema checker. | YAML parser flags and rejects any file in `Knowledge/` missing ID, Title, or Domain metadata. | Ingestion pipeline indexes files with incomplete or empty metadata blocks. |
