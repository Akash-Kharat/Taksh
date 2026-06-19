# Memory Architecture Specification — Taksh v0.1
**Cognitive State Engine, Consolidation Pipelines, and Privacy Safeguards**

> [!NOTE]
> This document specifies the memory systems architecture for Taksh, a voice-enabled engineering mentor with memory. It details the hierarchical cognitive memory model, storage layer, retrieval engine, memory aging rules, importance scoring mechanics, and local privacy constraints.

---

## 1. Cognitive Memory Model

Taksh implements a multi-tier memory system designed to balance high-speed real-time context ingestion with long-term retention of project standards and personal developer profiles. The model is structured into five distinct memory types, mapping directly to human cognitive categories:

```mermaid
graph TD
    subgraph UI [Developer Workstation / IDE]
        A[Cursor / Active File / Compiler Errors]
        B[User Voice / Chat Input]
    end
    subgraph Session [Session Memory - Volatile]
        C[Sensory Buffer]
        D[Active Session Transcript]
        E[Active Goals & task.md]
    end
    subgraph Storage [Persistent Memory Layer]
        F[(SQLite DB: taksh.db)]
        G[(ChromaDB Vector Store)]
        H[project_memory.md]
    end
    subgraph Processing [Retrieval & Synthesis]
        I[Knowledge Strategy RAG]
        J[Gemini Live API Context]
    end

    A -->|Streaming Telemetry| C
    B -->|Ingested Turns| D
    C -->|Synthesized on Session End| D
    D -->|Write/Read Task State| E
    E <-->|Sync| H
    D -->|Nightly Consolidation| F
    D -->|Nightly Consolidation| G
    F -->|Load Preferences / Profile| J
    G -->|Retrieve Past Lessons| J
    H -->|Inject Project Rules| J
    I -->|Dynamic Knowledge Chunks| J
```

### Memory Type Classification

| Memory Type | Cognitive Category | Storage Backend | Lifetime | Read Latency | Typical Volume |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Session Memory** | Working Memory / Sensory Buffer | Volatile (In-Memory Python Dict) | Active session cycle (discarded on disconnect) | $\le 10\text{ms}$ | 10–50 KB |
| **Project Memory** | Semantic & Procedural (Local) | local Markdown (`project_memory.md` & `task.md`) | Persistent for the repository | $\le 50\text{ms}$ | 10–100 KB |
| **Long-Term Memory** | Episodic & Semantic (Global) | Local ChromaDB & SQLite (`taksh.db`) | Permanent (Years) | $\le 150\text{ms}$ | 10–100 MB |
| **User Preferences** | Developer Profile / Mastery | Local SQLite (`taksh.db`) | Permanent (Cross-Project) | $\le 20\text{ms}$ | 100–500 KB |
| **Knowledge References**| Declarative Grounding Cache | Local ChromaDB & BM25 Index | Dynamic (re-indexed on source modification) | $\le 120\text{ms}$ | 50–500 MB |

---

### Memory Type Details

#### A. Session Memory
Captures the immediate workspace telemetry and the active conversational exchange.
*   **Sensory Buffer**: Continually tracks the active file path, visible cursor line, selected code blocks, and compiler or terminal stdout/stderr trace streams. This is updated via the IDE websocket telemetry at 1Hz.
*   **Working Context**: Maintains the active dialogue transcript (text representations of user and assistant voice utterances) for the last 15 turns.

#### B. Project Memory
Captures the development context unique to the current workspace repository.
*   **System Constraints**: Repository-specific rules, such as mandatory testing frameworks (e.g., "Must use pytest for all tests"), disabled standard library headers (e.g., "malloc forbidden in ISRs"), and target chip definitions.
*   **Active Goals**: The active engineering task list (`task.md`), tracking progress, blocking issues, and pending implementations.

#### C. Long-Term Memory
Stores cross-project engineering insights and experiences.
*   **Episodic Memory**: Narratives of resolved bugs, debug loops, and architectural design choices. For example: "On project X, ESP32 DMA transfers crashed when the source buffer was not word-aligned. Resolved by aligning buffers to 4-byte boundaries."
*   **Lessons Learned**: High-level generalizations of software patterns synthesized from past debugging sessions.

#### D. User Preferences
Stores profiles of the developer to guide the conversational personality, pedagogy, and Socratic boundaries.
*   **Developer Profile**: seniority level (junior, mid, senior), primary technology stacks, and stylistic preferences (e.g., Object-Oriented vs. Functional).
*   **Mastery Index**: Concept-level comprehension scores (e.g., "FreeRTOS Mutexes: 85%", "C-style pointers: 40%") mapped to adjust the technical depth of explanations.

#### E. Knowledge References
Maintains vectorized anchors pointing to local codebase documentation, third-party libraries, and chip datasheets.
*   **Documentation Chunks**: Semantic blocks of crawled documentation sheets.
*   **Semantic Anchors**: Mapping profiles linking specific compiler errors or API symbols directly to local knowledge files (e.g., error `ESP_ERR_NO_MEM` resolves to [ESP32 Partition Management](file:///d:/Taksh/Knowledge/04_esp32/esp_idf/partition_tables.md)).

---

## 2. Storage Strategy

Taksh utilizes a hybrid storage architecture: SQLite for structured relational relationships and fast telemetry updates, ChromaDB for semantic vector searches, and Markdown files for developer-inspectable configuration and transparent project rules.

```
.taksh/                          # Project root-level configuration directory
├── taksh.db                     # Relational SQLite database (profile, settings, log metadata)
├── chroma/                      # ChromaDB storage directory (embeddings)
│   ├── chroma.sqlite3
│   └── index_data/
├── memory/                      # Markdown-based session logs & human preferences
│   ├── session_history/         # Serialized raw session transcript logs
│   │   ├── session_001_log.md
│   │   └── session_002_log.md
│   └── project_memory.md        # Human-editable project memory and rules
└── identity/
    └── core_identity.md         # Read-only Core Identity document (personality baseline)
```

### Relational Database Schema (SQLite)

The SQLite database (`taksh.db`) operates as the relational registry tracking user profiles, mastery vectors, session metadata, and trust calculations.

```mermaid
erDiagram
    USER_PROFILE ||--o{ LEARNING_HISTORY : tracks
    USER_PROFILE ||--o{ SESSION_LOGS : records
    USER_PROFILE ||--|| TRUST_METRICS : evaluates

    USER_PROFILE {
        int user_id PK
        string developer_level "junior | mid | senior"
        text primary_stack "JSON array of frameworks"
        text style_preferences "JSON of architectural paradigms"
        boolean socratic_mode "Default True"
        string voice_personality "mentor | engineer | teacher"
    }
    LEARNING_HISTORY {
        string concept_id PK
        string concept_name
        int mastery_score "0 to 100"
        timestamp last_reviewed
        int interaction_count
        int review_interval "In days, for spaced retrieval"
    }
    SESSION_LOGS {
        string session_id PK
        timestamp start_time
        timestamp end_time
        text transcript "Serialized JSON conversation turns"
        int interrupted_turns "Count of user interruptions"
        text skills_used "JSON array of active skills"
    }
    TRUST_METRICS {
        int user_id PK
        float trust_score "0.0 to 100.0"
        float socratic_engagement_rate "User response rate to cues"
        timestamp last_updated
    }
```

### Vector Database Collections (ChromaDB)

Vector storage uses a locally run sentence-transformer (`all-MiniLM-L6-v2`, 384 dimensions) for semantic lookup.

#### 1. Collection: `long_term_episodes`
Stores synthesized narratives of resolved issues, design reviews, and lessons learned.
*   **Vector**: Embeddings of the synthesized lesson narrative.
*   **Metadata**:
    ```json
    {
      "session_id": "uuid-v4",
      "timestamp": "2026-06-19T18:16:19Z",
      "tags": ["esp32", "dma", "memory-alignment"],
      "project_name": "Taksh",
      "importance_score": 0.85
    }
    ```

#### 2. Collection: `project_rules`
Stores vectorized architectural rules extracted from codebases or explicitly declared by the user.
*   **Vector**: Embeddings of the rule statement.
*   **Metadata**:
    ```json
    {
      "project_name": "Taksh",
      "rule_type": "architectural_constraint",
      "date_added": "2026-06-19"
    }
    ```

#### 3. Collection: `knowledge_chunks`
Stores semantic blocks from the workspace and external documentation.
*   **Vector**: Embeddings of the document chunk.
*   **Metadata**:
    ```json
    {
      "doc_id": "K-03-SYNCH-02",
      "domain": "freertos",
      "tags": ["queues", "interrupts"],
      "synonyms": ["Message Queue", "FreeRTOS Queue"]
    }
    ```

### Markdown File Formats

#### A. `project_memory.md`
Located in the local workspace directory, this file is fully editable by the developer and read by Taksh at initialization. It acts as the explicit control sheet for project context.

```markdown
# Taksh Project Memory — [Project Name]

## System Constraints
*   **Target hardware**: ESP32-S3 (WROOM-1 module)
*   **SDK version**: ESP-IDF v5.1
*   **Memory constraints**: Strict partition sizing; no dynamic heap allocations inside ISR handlers.
*   **Prohibited libraries**: Avoid C++ Standard Template Library (STL) due to runtime memory overhead.

## Architectural Preferences
*   **Design Pattern**: Layered clean architecture separating device drivers from scheduling tasks.
*   **Error Handling**: Must check and propagate `esp_err_t` return codes up to system monitoring.

## Active Project Goals
- [x] Configure dual-core FreeRTOS task distribution.
- [/] Resolve high-priority queue contention inside `audio_stream_task`.
- [ ] Implement OTA flash fallback partitions.

## Lessons Learned (Consolidated)
*   *2026-06-18*: Audio buffer allocation failed on startup because the heap was fragmented by log task initialization. **Solution**: Initialize the audio buffer globally before launching secondary tasks.
```

---

## 3. Retrieval Strategy

To supply the LLM with relevant context without causing token bloat or context drift, Taksh executes a multi-stage, hybrid retrieval pipeline upon receiving user inputs.

```mermaid
sequenceDiagram
    autonumber
    participant Watcher as IDE / Workspace Watcher
    participant Orch as Orchestrator
    participant SQL as SQLite DB
    participant Chroma as ChromaDB Vector Store
    participant Gemini as Gemini Live API

    Watcher->>Orch: Telemetry Update (Active file, cursor, compiler error)
    User->>Orch: Speaks: "Why is my queue post failing inside the ISR?"
    Note over Orch: Query Expansion: Maps 'queue post' -> 'xQueueSendToBackFromISR'
    Orch->>SQL: Query user profile, mastery levels, & trust metrics
    SQL-->>Orch: User: mid-level; FreeRTOS mastery: 45%; Socratic: Enabled
    Orch->>Chroma: Query long_term_episodes (Semantics of "queue post ISR fail")
    Chroma-->>Orch: Top episodic match: "xQueueSendFromISR requires pxHigherPriorityTaskWoken"
    Orch->>Chroma: Query knowledge_chunks (Filter: domain="freertos")
    Chroma-->>Orch: Top 2 chunks: FreeRTOS ISR rules & stack limits
    Orch->>Orch: Compile system prompt & dynamic context payload
    Orch->>Gemini: Stream user audio + Injected context payload
```

### Context Aggregation & Prompt Ingestion

The orchestrator dynamically builds the context payload injected at the initialization of the Gemini Multimodal Live session. This payload consists of five sections:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Core Identity (Pedagogical Socratic Directive)           │
├─────────────────────────────────────────────────────────────┤
│ 2. Developer Profile & Mastery Settings                      │
│    - Seniority Level: Mid-Level                             │
│    - Socratic Toggle: ON                                    │
│    - FreeRTOS mastery: 45% (Explain scheduler details)      │
├─────────────────────────────────────────────────────────────┤
│ 3. Workspace Telemetry (Sensory State)                      │
│    - Active File: /src/main.c                               │
│    - Selection Range: lines 122-135                         │
│    - Compiler Output: "Error: task_create conflicting types"│
├─────────────────────────────────────────────────────────────┤
│ 4. Retrieved Memory Context                                 │
│    - Project Constraint: "ESP-IDF v5.1, no heap in ISR"     │
│    - Long-Term Episode: "Word-alignment crash on ESP32-S3"  │
│    - Knowledge Chunk: "How to use xQueueSendFromISR"        │
├─────────────────────────────────────────────────────────────┤
│ 5. Conversational State & Dialog History (Last 10 turns)     │
└─────────────────────────────────────────────────────────────┘
```

### Hybrid Retrieval Mechanics

1.  **Semantic Expansion**: Before vector query processing, terms are mapped to synonyms loaded from `knowledge_chunks` schemas (e.g., mapping user input "IPC queue" to `xQueueSend` or `modbus register` to `Modbus RTU frame`).
2.  **Metadata Pre-Filtering**: Queries targeting ChromaDB vector collections are restricted using active codebase constraints (e.g., querying `knowledge_chunks` restricts search to `domain: "freertos"` and `domain: "esp32"` when active files are C files containing Espressif headers).
3.  **Cross-Encoder Reranking**: The top 15 candidate passages returned by vector search (ChromaDB) and syntactic search (BM25 keyword match) are evaluated using a local, lightweight Cross-Encoder model (`bge-reranker-base`). The top 3 ranked chunks are injected as the context payload.

---

## 4. Memory Aging Policy

To prevent database bloat, performance degradation, and context drift, Taksh implements a system of progressive memory decay and consolidation.

```mermaid
stateDiagram-v2
    [*] --> SensoryState : User Interaction
    SensoryState --> SessionLog : Session Closes (Transient Archive)
    SessionLog --> StoredEpisodes : Nightly Consolidation (I >= 0.5)
    SessionLog --> Purged : 30-Day Expiry (I < 0.5)
    StoredEpisodes --> ActiveVectors : High retrievability (R >= 0.2)
    StoredEpisodes --> ColdStorage : Memory decay (R < 0.2)
    ColdStorage --> Purged : Long-term pruning (R < 0.05)
```

### Decay and Consolidation Lifecycle

#### Phase 1: Volatile Sensory Pruning
Sensory memory (cursor location, selections, compiler outputs) is cleared completely upon closing the IDE or disconnecting the voice companion session.

#### Phase 2: Session Archive
Conversation transcripts and activated skills are compiled into a raw JSON log and saved as `.taksh/memory/session_history/session_XXX_log.md` for historical traceability. These files are kept for a maximum of 30 days unless flagged for consolidation.

#### Phase 3: Nightly Consolidation Pipeline
A background process runs daily to review the transient session logs:
1.  **Relevance Filtering**: Evaluates session events using the **Importance Scoring Engine** (see Section 5).
2.  **Episodic Extraction**: If a session log contains a resolved technical issue or architectural debate with an importance score $I \ge 0.5$, a local LLM summarizer generates a structured episode card:
    *   **Problem Statement**: The symptoms and compiler traces observed.
    *   **Root Cause**: The physical or logical source of the failure.
    *   **Actionable Solution**: The specific code modification or configuration change that fixed the issue.
3.  **Index Updates**: The generated episode card is vectorized and appended to ChromaDB's `long_term_episodes` collection.
4.  **Markdown Sync**: The summary statement is appended to the "Lessons Learned" section of `project_memory.md`.

#### Phase 4: Long-Term Episodic Decay (Spaced Retrieval model)
To prioritize memory space for active concepts, episodic memories are subject to Ebbinghaus-derived retrievability decay. The retrievability $R(t)$ of a memory is computed as:

\[
R(t) = e^{-\frac{t}{S}}
\]

Where:
*   $t$ is the time elapsed (in days) since the memory was last recalled or updated.
*   $S$ is the memory strength parameter.

The memory strength $S$ increases dynamically upon successful recall:

\[
S_{new} = S_{old} \cdot (1 + \alpha \cdot T_{engagement})
\]

Where:
*   $\alpha$ is a scaling factor ($\alpha = 0.5$).
*   $T_{engagement}$ is the duration of user engagement with the recalled memory (scaled between 0.0 and 1.0).

*   **Retrievability Thresholds**:
    *   **$R(t) \ge 0.2$ (Active Vector)**: Injected directly into candidate RAG queries.
    *   **$0.05 \le R(t) < 0.2$ (Cold Storage)**: Removed from the high-speed ChromaDB runtime index to save memory. Kept in flat files (`taksh.db` archives) and only loaded if explicit keyword search matches are found.
    *   **$R(t) < 0.05$ (Purged)**: Permanently deleted from the system.

---

## 5. Memory Importance Scoring

Taksh uses an explicit Importance Scoring Model to evaluate whether a conversational interaction contains valuable insights that should be elevated to long-term memory.

### Importance Scoring Formula

At the end of a session, each dialog segment and engineering interaction is evaluated against four parameters to calculate the final importance score $I$:

\[
I = w_U \cdot U + w_E \cdot E + w_C \cdot C + w_A \cdot A
\]

Where the weights are defined as:
*   $w_U = 0.40$ (User Explicitness)
*   $w_E = 0.15$ (Emotional/Frustration Index)
*   $w_C = 0.25$ (Cognitive Resolution)
*   $w_A = 0.20$ (Architectural Relevance)

The sum of the weights: $\sum w_i = 1.0$.

### Parameter Specifications

#### 1. User Explicitness ($U \in \{0.0, 1.0\}$)
Indicates if the user explicitly commanded the assistant to record or remember a fact.
*   **$U = 1.0$**: Verbal commands containing triggers like *"remember that..."*, *"add to project rules..."*, *"our standard is..."*, or checking a task in `task.md`.
*   **$U = 0.0$**: Standard conversational flow without explicit memory commands.

#### 2. Emotional/Frustration Index ($E \in [0.0, 1.0]$)
Inferred from conversation indicators, signifying a high-friction debug loop.
*   **Indicators**:
    *   Number of consecutive compiler execution failures with identical error structures ($+0.25$ per retry, max $0.50$).
    *   Density of user questions within a 3-minute window ($>5$ queries $= +0.25$).
    *   Voice tone descriptors (e.g., high speech rate or volume fluctuation, $+0.25$).

#### 3. Cognitive Resolution ($C \in [0.0, 1.0]$)
Measures if a complex task was successfully resolved.
*   **$C = 1.0$**: The user compiler errors resolve, files compile, and the developer verbally confirms (e.g., *"that worked"*, *"compilation succeeded"*, *"got it working"*).
*   **$C = 0.0$**: The session terminated with unresolved compilation errors or active task warnings.

#### 4. Architectural Relevance ($A \in [0.0, 1.0]$)
Measures the depth of modifications in the codebase.
*   **$A = 1.0$**: The changes involve architectural files (headers `.h`, config files `sdkconfig`, database schemas, routing modules, API declarations).
*   **$A = 0.5$**: The changes affect application-level implementation logic.
*   **$A = 0.0$**: The interaction is conceptual, conversational, or general Q&A with no file modifications.

### Score Threshold Actions

```
               [ Calculated Score I ]
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
      I >= 0.8      0.5 <= I < 0.8     I < 0.5
      ┌──────┐      ┌────────────┐    ┌───────┐
      │Active│      │   Nightly  │    │Session│
      │Rules │      │Queue / Sync│    │Logs   │
      └──────┘      └────────────┘    └───────┘
```

*   **$I \ge 0.8$ (Immediate Elevation)**: The episode is immediately vectorized, written to the ChromaDB `long_term_episodes` collection, and appended to `project_memory.md` under the "Lessons Learned" header.
*   **$0.5 \le I < 0.8$ (Consolidation Queue)**: Placed in the queue for evaluation by the nightly cron job.
*   **$I < 0.5$ (Discard/Archive)**: Kept in raw session transcripts only. Subject to pruning after 30 days.

---

## 6. Privacy Model

As a developer sidecar utility, Taksh is built around a local-first security architecture to guarantee that intellectual property, proprietary source files, and credentials never leak to external platforms.

```mermaid
graph LR
    subgraph Local_Workstation [Local Workspace - Secure Boundary]
        code[Source Code / IDE]
        db[(SQLite / ChromaDB)]
        scrub[Scrubbing & Redaction Engine]
    end
    subgraph External_Cloud [External Cloud - LLM Endpoint]
        Gemini[Gemini Live API]
    end

    code -->|Raw Data| scrub
    db -->|Raw Context| scrub
    scrub -->|Redacted Payload| Gemini
    Gemini -->|Streaming Audio/Text| code
```

### Local-First Boundary Rules
1.  **No Cloud Databases**: SQLite databases, ChromaDB collections, and text logs are stored exclusively in the `.taksh/` directory inside the developer's local workspace. No metadata, vectors, or telemetry are synchronized to external cloud databases.
2.  **Local Network Binding**: The FastAPI companion process binds strictly to loopback IP addresses (`127.0.0.1` / `localhost`). Port 8000 is blocked from external interfaces, preventing unauthorized access from local area networks (LAN).

### Data Scrubbing & Redaction Pipeline
Before any prompt context, transcript, or code block is sent to the Gemini Multimodal Live API websocket, it passes through an in-memory streaming redact filter.

*   **API Key Redaction**: Scans for standard entropy structures and key prefixes (`AIzaSy...` for Google, `sk-...` for OpenAI, `AKIA...` for AWS) using pre-compiled regex rules. Matches are replaced with `[REDACTED_API_KEY]`.
*   **Secret & Password Filtering**: Redacts connection strings (e.g., `mongodb://user:pass@host`), database credentials, and SSL private key headers.
*   **PII Anonymization**: A lightweight, offline Named Entity Recognition (NER) model checks transcripts for emails, names, and phone numbers, substituting them with placeholders (e.g., `[REDACTED_EMAIL]`).
*   **Gitignore Compliance**: The Workspace Watcher parses the repository `.gitignore` and ignores any files, log dumps, or build outputs located in ignored subdirectories.

### Transmission Boundaries
*   **Explicit Consent for Web Search**: When using the *Research Assistant* skill, Taksh will verbally prompt the user before initiating web searches (e.g., *"I need to run a web search to check the ESP32-S3 sleep current specifications. Is that okay?"*).
*   **Local Codebase Isolation**: Only files that are open in the developer's active workspace, or files explicitly referenced by the user, are loaded into memory. Massive codebase crawling is blocked unless a manual command triggers workspace ingestion (`POST /api/v1/knowledge/ingest`).
