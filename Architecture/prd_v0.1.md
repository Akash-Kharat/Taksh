# Product Requirements Document (PRD) — Taksh v0.1
**Voice-Enabled Engineering Mentor with Memory**

---

## 1. Problem Statement
Modern software engineering has become a highly fragmented cognitive task. Developers regularly jump between writing code, searching documentation, debugging stack traces, and reviewing system designs. While AI code assistants exist, they suffer from several structural flaws:
1. **Context Fragmentation**: Assistants lose track of architectural decisions, user preferences, and historical design debates across coding sessions.
2. **Keyboard Friction**: Forcing the user to type out long conceptual explanations or walk through design options disrupts the flow state and deters deep system reflection.
3. **Passive Code Generation (Copy-Paste Development)**: Most assistants operate as reactive code generators, producing code without explaining the underlying patterns or validating architectural choices, which increases technical debt and diminishes user agency.

**Taksh v0.1** addresses this by introducing a **voice-enabled, memory-persistent engineering mentor**. It acts as a real-time cognitive sounding board, utilizing voice to minimize input friction and a tiered memory system to maintain long-term contextual continuity. It focuses on guiding the engineer through first principles, teaching concepts, and reviewing architectures rather than just generating raw text output.

---

## 2. User Personas

### Persona A: Siddharth — The Eager Junior/Mid-level Engineer
*   **Role**: Software Engineer at a rapidly scaling fintech startup.
*   **Needs**: 
    *   To understand *why* certain design patterns (e.g., CQRS, Hexagonal Architecture) are preferred over others.
    *   A safe, interactive environment to debug complex compiler/runtime errors without feeling judged by peers.
    *   Explanations that start from simple terms and scale up to detailed API constraints.
*   **Frustrations**:
    *   Standard code-generation tools give him working code but do not explain the logic, leading to gaps in his knowledge.
    *   Pasting large error traces and explaining context in text blocks is tedious and disrupts his debugging loop.
*   **Taksh Value**: Serves as a **Socratic Teacher and Mentor**, engaging in voice-based debug sessions and forcing him to think through edge cases rather than spoon-feeding solutions.

### Persona B: Elena — The Pragmatic Systems Architect
*   **Role**: Lead Systems Architect at a distributed logistics enterprise.
*   **Needs**:
    *   A high-level design partner to review microservice dependencies and verify resilience patterns.
    *   Quick, synthesized research on technical libraries, performance profiles, and RFC specifications.
    *   An agent that respects and references historical architecture decisions made in the codebase.
*   **Frustrations**:
    *   AI assistants don't remember the project constraints (e.g., "we do not use library X because of licensing issues") across sessions.
    *   Explaining complex database schema changes takes too long in a standard chat box.
*   **Taksh Value**: Serves as a **Rigorous Researcher and Strategic Guide**, using project memory to maintain compliance with architectural rules and conducting multi-step research synthesis in the background.

---

## 3. Functional Requirements

### 3.1. Voice Conversation (Companion / Mentor Facets)
*   **FR-1.1: Hands-Free Voice Channel**: Provide a bidirectional voice session with natural-sounding text-to-speech (TTS) and speech-to-text (STT).
*   **FR-1.2: Voice Activity Detection (VAD)**: The system must automatically detect when the user is speaking and when they stop, eliminating the need to manually toggle a record button.
*   **FR-1.3: Real-Time Interruption**: The user must be able to speak over the AI's audio response. The system must immediately stop its audio output, transition back to listening mode, and process the user's input.
*   **FR-1.4: Dual-Channel UI**: Render a live-scrolling, sync-locked text transcript of the voice exchange alongside the active voice channel to allow visual review of commands, paths, and code snippets.
*   **FR-1.5: Keyboard & Toggle Controls**: Establish high-priority global hotkeys to toggle voice mode (mute/unmute, start/stop session).

### 3.2. Knowledge Base (Teacher / Researcher Facets)
*   **FR-2.1: Codebase Documentation RAG**: Automatically ingest local markdown files, READMEs, architecture decision records (ADRs), and API specs.
*   **FR-2.2: External Documentation Ingestion**: Allow the user to point the agent to external documentation URLs (e.g., standard library docs, library references). The agent must parse and index these resources locally.
*   **FR-2.3: Semantic Search & Retrieval**: Ensure the agent can query the local vector store to retrieve relevant context when asked technical questions.

### 3.3. Session Memory (Sensory / Working Memory)
*   **FR-3.1: Transient Session State**: Track files opened, code selection, active terminal errors, and user cursor movements in the current session (Tier 1: Sensory Memory).
*   **FR-3.2: Short-term Task Tracking**: Maintain a checklist of tasks (`task.md`) and implementation plans active in the current session (Tier 2: Working Memory).
*   **FR-3.3: Post-Session Summary**: At the end of a voice session, automatically generate a concise, markdown-formatted summary of decisions made, files edited, and outstanding tasks, saving it to a session log folder.

### 3.4. Project Memory (Long-Term Memory)
*   **FR-4.1: Persistent Project Preferences**: Maintain a persistent local memory file (e.g., `memory.md` or a JSON database) tracking persistent project-scoped context (Tier 3: Long-Term Memory).
*   **FR-4.2: Architectural Decision Log**: Log structural decisions agreed upon during conversations, allowing the agent to reference them in future sessions (e.g., "In session 3, we decided to use PostgreSQL for audit logs due to transaction support").
*   **FR-4.3: Memory Pruning & Synthesis**: Run background tasks to consolidate and prune the persistent store, avoiding token bloat and context drift.

### 3.5. Engineering Assistance (Builder / Mentor Facets)
*   **FR-5.1: Context-Aware Debugging**: Analyze active runtime errors, stack traces, or build failure logs and present structured fixes via voice or text.
*   **FR-5.2: Code Modification Proposals**: Generate clean, precise diffs for proposed changes. *Note: For safety and alignment, direct edits require explicit user confirmation.*
*   **FR-5.3: Scaffolding Mode**: Provide high-level guidance, pseudo-code, and structural maps instead of raw copy-paste code blocks, prompting the user to write their own implementation to maintain agency.

### 3.6. Research Assistance (Researcher Facet)
*   **FR-6.1: Multi-Step Web Synthesis**: Execute multi-turn web search flows to gather documentation, compare libraries, and discover API usage patterns.
*   **FR-6.2: Grounded Citations**: Compile comparative matrices (tables) for library evaluations, citing the sources, versions, and publication dates.

### 3.7. Architecture Review (Companion / Guide Facets)
*   **FR-7.1: Module & Dependency Auditing**: Audit files or directories to construct module maps and dependencies, identifying tight coupling or circular dependencies.
*   **FR-7.2: Architectural Anti-Pattern Detection**: Proactively identify anti-patterns (e.g., bloated controllers, direct database queries from UI components, insecure API patterns) and recommend refactors.
*   **FR-7.3: Mermaid Visualizations**: Generate visual diagrams (Mermaid format) representing system architectures, sequence flows, or data models.

### 3.8. Learning Support (Teacher / Mentor Facets)
*   **FR-8.1: Socratic Coaching Toggle**: Introduce a mode where the agent acts purely Socratically—refraining from giving direct answers, instead asking leading questions to guide the engineer's discovery.
*   **FR-8.2: "Grill-Me" Interactive Mode**: Allow the user to request an oral mock interview/grilling session about an architectural decision or technical concept to stress-test their design.

---

## 4. Non-Functional Requirements

### 4.1. Performance & Latency
*   **NFR-1.1: Audio Latency**: The voice response latency (time from when the user stops speaking to the start of the audio response) must be $\le 1.2$ seconds under normal network conditions.
*   **NFR-1.2: Transcription Sync**: Text transcriptions must match audio playback within 200ms.

### 4.2. Privacy & Data Sovereignty
*   **NFR-2.1: Local Memory Storage**: All memory tiers (sensory, working, and long-term vector/key-value stores) must reside locally on the developer's machine.
*   **NFR-2.2: Sensitive Data Filtering**: Automatically redact credentials, secrets, and personal identifiable information (PII) before transmitting transcripts or code snippets to remote LLM APIs.
*   **NFR-2.3: Explicit Transmission Boundaries**: Prompt the user before executing external web searches or document ingestion that transmits project context.

### 4.4. Interface & Usability
*   **NFR-3.1: Visual System Status**: Provide clear, dynamic UI indicators for the agent's current state: *Listening*, *Processing (Thinking)*, *Speaking*, or *Offline*.
*   **NFR-3.2: Device Adaptability**: The interface must adapt cleanly to different window sizes, enabling side-by-side split screen with standard IDEs (e.g., VS Code).

---

## 5. Success Metrics

| Metric | Target | Measurement Method |
| :--- | :--- | :--- |
| **Response Latency (RT)** | Median (p50) $\le 1.0\text{s}$, p95 $\le 1.8\text{s}$ | Automatic network/API telemetry tracking. |
| **Interruption Success Rate** | $\ge 95\%$ responsiveness to voice interruptions | Telemetry counting interruption events and audio cuts. |
| **Engineering Progress Efficiency** | $\ge 30\%$ reduction in dev search-to-build loop time | Longitudinal study or task-completion tracking. |
| **Memory Recall Accuracy** | $\ge 90\%$ relevance in project memory RAG retrieval | Manual evaluation of retrieved memory contexts. |
| **Socratic Session Retention** | $\ge 40\%$ return rate for "grill-me" or review sessions | Weekly active user cohort telemetry. |

---

## 6. Risks & Mitigations

*   **Risk 1: Conversational Lag (Latency)**
    *   *Description*: High audio generation latency breaks the conversational illusion and causes frustration.
    *   *Mitigation*: Stream TTS audio chunks instantly as they are generated by the model instead of waiting for the full response; utilize lightweight WebRTC transport.
*   **Risk 2: Context Drift & Hallucinations**
    *   *Description*: The mentor recommends incorrect libraries or hallucinates architectural patterns.
    *   *Mitigation*: Implement a strict "Double-Check" cycle where the agent runs a local search/audit of documentation before confirming technical specifications.
*   **Risk 3: Memory Bloat / Noise**
    *   *Description*: Project memory accumulates outdated debug logs or minor code iterations, cluttering context.
    *   *Mitigation*: Execute a nightly/weekly offline memory consolidation run to compile transient session logs into high-level lessons learned and architecture profiles.
*   **Risk 4: User Distraction**
    *   *Description*: Constant interruptions or overly wordy verbal explanations break the developer's flow.
    *   *Mitigation*: Enforce a strict "first-principles, low-filler" verbal communication constraint. Keep verbal summaries short, offloading code blocks to the visual panel.

---

## 7. MVP Scope (v0.1)

The focus of the MVP is to prove the viability of voice-enabled mentoring with contextual session and project memory:

*   **In-Scope Core Features**:
    1.  **Web-Based Client**: Standalone, responsive web dashboard containing:
        *   An active voice channel control widget.
        *   A live-updating chat transcript panel.
        *   A project memory overview panel showing currently stored user rules and past decisions.
    2.  **Voice Loop (Whisper STT / Gemini / TTS)**: A cloud-backed WebRTC voice processing pipeline.
    3.  **Local Memory Files**: File-system based memory stores:
        *   `.taksh/session_history/` for raw session logs.
        *   `.taksh/project_memory.md` for persistent long-term project context.
    4.  **Engineering & Architecture Voice Review**: Ability to feed open workspace files into the system and talk through bugs or module structures.
    5.  **Basic Document Ingestion**: Parsing of local `.md` documents in the repository workspace.

---

## 8. Out-of-Scope Features for v0.1

The following capabilities are excluded from v0.1 and deferred to the Year 2/3 roadmap:

*   **Native IDE Plugins**: Dedicated extensions for VS Code, JetBrains, or Vim (v0.1 runs as a companion browser app).
*   **Autonomous File Writing**: Taksh will not write or refactor codebase files directly on disk without a manual git-apply or explicit user-facing visual diff check.
*   **Fully Offline Operation**: Local execution of audio transcripion and LLMs is deferred (requires massive local hardware); v0.1 relies on cloud APIs with strict data protection compliance.
*   **Multi-Agent Networks**: Task delegation to parallel autonomous subagents (e.g., automatic QA agents, automated PR refactorers).
*   **Integration with Local Language Servers (LSP)**: Automatic compiler diagnostics via LSP are deferred to v0.2.
