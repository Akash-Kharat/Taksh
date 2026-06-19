# System Architecture Document — Taksh v0.1
**Voice-Enabled Engineering Mentor with Memory**

---

## 1. System Architecture

Taksh v0.1 is designed as a **local sidecar companion service** that runs directly on the developer's workstation. This architecture maximizes privacy, provides zero-latency access to the local workspace, and enables offline vector and relational databases while leveraging cloud-based, low-latency AI endpoints for audio processing.

The system uses a **WebSocket-proxy orchestration pattern**: the React frontend maintains a single WebSocket connection with the FastAPI backend, which in turn orchestrates RAG, memory layers, and the Skills Engine, managing a persistent secure WebSocket tunnel to the Gemini Multimodal Live API.

### High-Level System Diagram

```mermaid
graph TD
    subgraph Frontend [Client - React + Vite SPA]
        A[Browser UI / Dashboard]
        B[Audio Capture & VAD]
        C[Audio Playback Engine]
    end
    subgraph Backend [Local Companion - FastAPI]
        D[API Gateway / WS Server]
        E[Voice Session Manager]
        F[Orchestrator / Dispatcher]
        G[Skills Engine]
        H[Memory Manager]
        I[Knowledge Base RAG Engine]
    end
    subgraph LocalStorage [Local Storage - .taksh/]
        J[(SQLite DB: taksh.db)]
        K[(ChromaDB Vector Store)]
        L[Local Workspace Markdown]
    end
    subgraph External [External APIs]
        M[Gemini Multimodal Live WebSocket API]
    end

    A <-->|HTTP/REST Config| D
    B -->|Streaming Audio PCM via WS| D
    D -->|Audio PCM & Transcript Stream| C
    D <--> E
    E <--> F
    F <--> G
    F <--> H
    F <--> I
    H <--> J
    I <--> K
    I <--> L
    E <-->|Multimodal WS Session| M
```

---

## 2. Component Diagram

The internal architecture is divided into decoupled modular boundaries to separate real-time media ingestion from database access, prompt engineering, and state watchers.

```mermaid
graph TD
    subgraph Client [Frontend React Client]
        subgraph Audio [Audio Module]
            AC[AudioCaptureEngine]
            AP[AudioPlaybackEngine]
            VAD[ClientVAD]
        end
        subgraph UI [UI Module]
            WS[WebSocketClient]
            ST[UIStateStore]
            WW[WorkspaceWatcher]
            DB[DashboardComponents]
        end
    end
    subgraph Server [Backend FastAPI Server]
        AG[API Gateway / Server]
        VSM[VoiceSessionManager]
        ORC[Orchestrator / Dispatcher]
        SE[SkillsEngine]
        MM[MemoryManager]
        KB[KnowledgeBaseRAGEngine]
        SQL[SQLiteClient]
        CH[ChromaDBClient]
    end

    VAD --> AC
    AC --> WS
    WS --> AP
    WS <--> AG
    AG <--> VSM
    VSM <--> ORC
    ORC <--> SE
    ORC <--> MM
    ORC <--> KB
    MM <--> SQL
    KB <--> CH
    WW --> AG
    DB <--> ST
    ST <--> WS
```

### Component Descriptions

#### Frontend Client
*   **AudioCaptureEngine**: Configures browser media devices, captures microphone input, and downsamples raw audio to 16kHz 16-bit mono PCM.
*   **AudioPlaybackEngine**: Coordinates playing raw PCM chunks received from the backend, manages an audio jitter buffer, and controls immediate audio queue flushes.
*   **ClientVAD**: Runs a lightweight voice activity detection algorithm (e.g., via `silero-vad` or Web Audio API Analyzer) in a web worker to detect speech boundaries, ensuring audio is only streamed when the user is speaking.
*   **WebSocketClient**: Handles connection state, reconnection logic, and routing of audio packets and JSON control messages.
*   **WorkspaceWatcher**: Emits periodic telemetry containing the user's active file, selection ranges, cursor positions, and terminal build failure traces.
*   **UIStateStore & Dashboard**: Manages UI modes (*Listening*, *Thinking*, *Speaking*, *Idle*) and displays the active conversation transcripts, long-term memory logs, and tasks.

#### Backend FastAPI Server
*   **API Gateway & VoiceSessionManager**: Exposes REST interfaces and acts as the entry point for WebSocket streams. Manages the connection lifecycle and proxying to external cloud endpoints.
*   **Orchestrator / Dispatcher**: Intercepts events, schedules database lookups, executes the Skills Engine, coordinates RAG, and builds the payload injected into the streaming LLM channel.
*   **SkillsEngine**: Loads specialized developer personas and executes prompt overlay mapping based on active context.
*   **MemoryManager**: Coordinates CRUD operations across SQLite, ChromaDB, and the immutable local Core Identity Memory.
*   **KnowledgeBaseRAGEngine**: Processes local workspace markdown files, generates embeddings, and queries ChromaDB for semantic retrieval.

---

## 3. Data Flow

The data flow highlights the lifecycle of a single voice query, demonstrating how memory retrieval, vector knowledge base searches, and the skills registry are executed before triggering the persistent LLM session, alongside how voice interruptions are handled.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser as Client Browser
    participant API as FastAPI Backend
    participant Gemini as Gemini Live API
    participant DB as SQLite / ChromaDB

    User->>Browser: Speaks "How do I queue in FreeRTOS?"
    Note over Browser: Client VAD detects start of speech
    Browser->>API: WS Connection / Start Stream
    Browser->>API: Audio Stream (PCM Chunks)
    Note over API: VAD boundary reached (speech end detected)
    API->>DB: Query memory (Sensory, Working, Long-Term, Core Identity)
    DB-->>API: Active file telemetry, active skill list, past ADRs
    API->>DB: Query Knowledge Base (ChromaDB)
    DB-->>API: FreeRTOS queue documentation chunk
    API->>API: Skills Engine activates 'FreeRTOS Expert'
    API->>Gemini: Establish WebSocket & send system instructions / RAG context
    API->>Gemini: Forward streaming user audio
    Gemini-->>API: Stream audio PCM + text tokens
    API-->>Browser: Forward audio stream & transcript
    Browser->>User: Play Audio / Render text transcript
    User->>Browser: Speaks over assistant (Interruption)
    Note over Browser: Client VAD detects user voice during playback
    Browser->>Browser: Halt Audio Playback & clear queues
    Browser->>API: WS: {"type": "interrupt"}
    API->>Gemini: Send cancellation signal / reset session
    API->>DB: Update Session Log (flag turn as interrupted)
```

---

## 4. Memory Architecture

Taksh implements a **4-tier hierarchical memory model** to maintain contextual continuity while managing token limits and avoiding context drift.

```mermaid
graph TD
    subgraph SensoryMemory [Sensory Memory - Volatile]
        S1[Active File Context]
        S2[Selected Code Blocks]
        S3[Compiler Errors]
        S4[Cursor Coordinates]
    end
    subgraph WorkingMemory [Working Memory - Short-Term]
        W1[Active Session Transcript]
        W2[Active Goals & Task List]
        W3[Active Implementation Plans]
    end
    subgraph LongTermMemory [Long-Term Memory - Persistent]
        L1[Architectural Decisions ADR]
        L2[User Coding Preferences]
        L3[Lessons Learned History]
    end
    subgraph CoreIdentityMemory [Core Identity Memory - Immutable]
        I1[Mission & Core Values]
        I2[Socratic Principles]
        I3[Personality & Boundaries]
    end

    SensoryMemory -->|Synthesized on Session End| WorkingMemory
    WorkingMemory -->|Consolidated in Background| LongTermMemory
    CoreIdentityMemory -->|Always Loaded First| WorkingMemory
```

### Memory Tier Specifications

| Memory Tier | Storage Backend | Lifetime | Contents | Pruning / Consolidation Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Sensory** | In-Memory (Python Dict) | Active session cycle (volatile) | Open file buffers, cursor lines, IDE selections, stack traces | Discarded upon session termination. |
| **Working** | SQLite / Local File (`task.md`) | Single engineering task lifecycle | Conversational context, checked/unchecked tasks, implementation plans | Archived to session logs on session close. |
| **Long-Term** | ChromaDB & SQLite (`taksh.db`) | Months / Years (Persistent) | Historical design debates, codebase architecture rules, developer profile | **Consolidation Pipeline**: Nightly background task processes logs, removes duplicates, and updates a semantic index. |
| **Core Identity** | Read-Only Markdown (`core_identity.md`) | Permanent | Mission, pedagogical principles, personality parameters, boundaries | **Strict Policy**: Never compressed, never pruned, never modified by LLM, always loaded. |

---

## 5. Core Identity Architecture

To ensure Taksh maintains an invariant personality and pedagogical baseline across all interactions, a dedicated **Core Identity Layer** is established. This layer is isolated from user memory, RAG indexes, and dynamic models, operating as a read-only foundation.

```mermaid
graph LR
    subgraph Storage [Identity Storage]
        CI_File[.taksh/identity/core_identity.md]
    end
    subgraph Runtime [Runtime Environment]
        Singleton[CoreIdentity Singleton Class]
        Orch[Session Orchestrator]
    end
    subgraph External [Inference Session]
        API_Call[Gemini System Prompt Payload]
    end

    CI_File -->|Read-Only Ingestion| Singleton
    Singleton -->|Immutable Cache| Orch
    Orch -->|Injected at Session Init| API_Call
```

### Identity Model
The identity model is defined declaratively using a structured markdown schema. It specifies Taksh's foundational role, values, and strict boundaries:
*   **Pedagogical Directive**: Always guide the developer towards understanding first principles. Avoid direct code generation unless the user demonstrates a conceptual grasp of the problem or has made multiple compilation attempts.
*   **Behavioral Baseline**: Be direct, encourage depth, ask clarifying questions, and respect the engineer's agency.

### Identity Storage Strategy
*   Stored in `.taksh/identity/core_identity.md`.
*   The backend establishes read-only filesystem file permission handles on this directory during initialization to prevent accidental overrides.

### Identity Runtime Architecture
*   Loaded into memory during backend application startup.
*   Parsed into a thread-safe python `Singleton` class (`CoreIdentityManager`).
*   The backend blocks any write API commands pointing to this directory.

### Identity Retrieval Mechanism
*   The raw string content of the Core Identity file is loaded at the start of every connection.
*   It is injected into the root `system_instruction` configuration of the Gemini Multimodal Live WebSocket setup payload, guaranteeing that the model maintains its core behavior throughout the connection lifecycle.

---

## 6. Personality Architecture

Taksh maintains a consistent core identity while adjusting its communication style and level of technical depth using five distinct operational modes.

### Personality Traits & Behavioral Rules
1.  **Pedagogical Rigor**: Respond with questions that push the user to locate root causes instead of immediately offering code fixes.
2.  **Architectural Meticulousness**: Always warn of tight coupling, circular dependencies, or security compromises in proposed solutions.
3.  **Low-Filler Dialogue**: Limit verbal output to key concepts. Code blocks, graphs, and comparative tables must be pushed to the visual dashboard, keeping audio dialogue clean.

### Personality Modes

```mermaid
stateDiagram-v2
    [*] --> CompanionMode : User joins
    CompanionMode --> MentorMode : Technical discussion starts
    MentorMode --> EngineerMode : Compile error / Debug request
    MentorMode --> TeacherMode : Conceptual breakdown request
    MentorMode --> ResearchMode : Library comparison request
    
    state ModeSelector <<choice>>
    EngineerMode --> ModeSelector : Debug resolved
    TeacherMode --> ModeSelector : Concept understood
    ResearchMode --> ModeSelector : Synthesis complete
    
    ModeSelector --> MentorMode : Continue task
    ModeSelector --> CompanionMode : Task finished / Idle
```

*   **Mentor Mode (Default)**: Leverages active Socratic coaching, asks leading questions, suggests high-level modules, and encourages clean code practices.
*   **Engineer Mode**: Switches to analytical debugging, processes compiler stack traces, suggests exact line modifications, and reviews code structures.
*   **Teacher Mode**: Utilizes architectural analogies, explains design history, and breaks down complex algorithms.
*   **Research Mode**: Triggers multi-step documentation searches, constructs library comparison tables, and highlights licenses and security vulnerabilities.
*   **Companion Mode**: Focuses on encouraging the developer, managing cognitive fatigue during long debug loops, and checking in on long-term task goals.

---

## 7. Relationship Model

To build deep trust and remain relevant over months of usage without becoming repetitive or intrusive, Taksh tracks user progress using a relational schema.

### Relationship Database Schema

```mermaid
erDiagram
    USER_PROFILE ||--o{ LEARNING_HISTORY : tracks
    USER_PROFILE ||--o{ GOAL_TRACKER : pursues
    USER_PROFILE ||--o{ PROJECT_TRACKER : manages
    USER_PROFILE ||--|| TRUST_METRICS : evaluates

    USER_PROFILE {
        int user_id PK
        string developer_level "Junior, Mid, Senior"
        string primary_stack "Rust, C, Python"
        json coding_style_preferences "e.g., FP vs OOP"
    }
    LEARNING_HISTORY {
        int concept_id PK
        int user_id FK
        string concept_name "e.g., FreeRTOS Semaphores"
        int mastery_score "0 to 100"
        datetime last_reviewed
    }
    GOAL_TRACKER {
        int goal_id PK
        int user_id FK
        string description
        string status "Active, Achieved"
        datetime target_date
    }
    PROJECT_TRACKER {
        int project_id PK
        int user_id FK
        string project_name
        json tech_stack
        json historical_adr_keys "Pointers to ChromaDB"
    }
    TRUST_METRICS {
        int user_id PK
        int interaction_count
        int help_usefulness_rating
        int socratic_compliance_score "How user responds to hints"
        float trust_score "Calculated 0.0 to 100.0"
    }
```

### Relationship Mechanics
*   **Trust Model**: Represents how the assistant adjusts its autonomy. High trust ($T > 75$) grants the assistant permission to suggest complex, pre-scoped design refactors. Low trust ($T < 40$) makes the assistant more conservative, requiring frequent confirmations.
*   **Continuous Learning Integration**: If a developer previously spent three sessions debugging *FreeRTOS queue allocation*, Taksh will reference this context in future sessions rather than explaining the concept from scratch.
*   **Non-Intrusive Continuity**: Long-term memory is queried silently via vector search on the active session topic. If a matching memory exists, it is loaded into the background context. The assistant only references past sessions when it is directly relevant to the current task.

---

## 8. Skills Engine Architecture

The Skills Engine shifts the LLM pipeline from a simple chat response to a structured tool-use workflow.

```mermaid
graph TD
    A[Voice Audio / User Query] --> B[Orchestrator]
    C[Workspace Telemetry] --> B
    B --> D[Skills Engine]
    D --> E{Skill Registry}
    E -->|Check triggers & keywords| F[Active Skills: ESP32 + FreeRTOS]
    F -->|Compile Prompt Overlay| G[Context Composer]
    B --> H[Memory Manager]
    H -->|Load Core Identity & User Profile| G
    B --> I[Knowledge RAG]
    I -->|Fetch doc chunks| G
    G --> J[Dynamic System Instruction]
    J --> K[Gemini Multimodal Live API]
    K --> L[Structured Voice & Text Response]
```

### Skill Registry & Active Skills (v0.1)
The engine loads metadata, prompting templates, and specialized tool interfaces for each skill:
*   **Embedded Architect**: Evaluates low-level resource limits, latency bounds, and hardware constraints.
*   **PCB Reviewer**: Guides high-level schematic checks, trace clearance requirements, and decoupling capacitor placement.
*   **ESP32 Firmware Engineer**: Specializes in ESP-IDF patterns, bootloader behavior, and hardware strapping pins.
*   **FreeRTOS Expert**: Identifies race conditions, deadlocks, task priority inversions, and heap allocation strategies.
*   **IoT Architect**: Analyzes MQTT QoS levels, secure TLS handshakes, data serialization overhead, and OTA strategies.
*   **Django Architect**: Enforces REST/GraphQL best practices, query optimization (N+1 queries), and database isolation.
*   **React Architect**: Guides state management, custom hook structures, components decoupling, and bundle optimization.
*   **Predictive Maintenance Engineer**: Guides vibration anomaly models, DSP sampling rates, and edge inference constraints.
*   **AI Architect**: Guides prompt engineering, vector search strategies, and deployment metrics.
*   **Research Assistant**: Executes multi-turn web search flows, compares software libraries, and verifies licenses.

### Skill Selection & Composition Strategy
1.  **Static Trigger Evaluation**: The Orchestrator monitors the active files in the workspace (sensory memory). For example, finding `sdkconfig` or `#include "freertos/FreeRTOS.h"` automatically registers the *ESP32 Firmware Engineer* and *FreeRTOS Expert* skills.
2.  **Semantic Intent Mapping**: If the user asks "How do we secure the MQTT broker payload?", the semantic classifier matches the query to the *IoT Architect* skill, adding its templates to the session context.
3.  **Collaborative Composition (Blackboard Pattern)**: Active skills write constraints to a shared session blackboard. The Orchestrator combines these constraints. For an IoT device running on an ESP32, the *FreeRTOS Expert* and *IoT Architect* skills combine their instructions, ensuring the generated advice covers both task safety and network efficiency.

---

## 9. Knowledge Architecture

The Knowledge Base houses in-repository documentation, READMEs, architectural decision records (ADRs), and ingested external documentation.

```mermaid
flowchart TD
    subgraph Ingestion [Ingestion Pipeline]
        A[Scan Local Workspace] --> B{Filter .gitignore}
        B -->|Valid MD| C[Structure-Aware Parser]
        C --> D[Semantic Chunking]
    end
    subgraph Indexing [Embedding & Storage]
        D -->|Text Chunks| E[Local SentenceTransformers Model]
        E -->|Vector Embeddings| F[(Local ChromaDB)]
        C -->|File Metadata| G[(SQLite Index)]
    end
    subgraph Querying [Retrieval Pipeline]
        H[User Input Query] --> I[Hybrid Search Orchestration]
        I -->|Vector Query| F
        I -->|FTS5 Keyword Query| G
        F & G --> J[Re-ranker & Context Synthesis]
        J -->|Top-K Context Chunks| K[LLM RAG Context Injected]
    end
```

### Chunking and Embedding Specifications
*   **Semantic Chunking**: Documents are split based on markdown structural headers. Each chunk preserves parent header strings to retain structural context. Chunks are capped at 500 tokens with a 10% overlap.
*   **Vector Engine**: Embeddings are generated using a locally-run SentenceTransformers model (e.g., `all-MiniLM-L6-v2`), ensuring complete privacy and offline usability.
*   **Hybrid Retrieval**: Combines ChromaDB semantic similarity search with SQLite FTS5 keyword indexing, ensuring specific code identifiers, system terms, and architectural patterns are retrieved accurately.

---

## 10. Voice Architecture

The Voice Architecture manages real-time, bidirectional voice streaming with sub-second response times and support for natural interruptions.

```mermaid
graph TD
    subgraph Client_Audio [Client Browser]
        Mic[Microphone Input] --> VAD[Client VAD]
        VAD -->|Active Audio| WS_Out[WebSocket Send]
        WS_In[WebSocket Recv] --> Playback[Audio Playback Engine]
        VAD -->|Interruption Event| Interrupt[Clear Playback Queue]
    end
    subgraph Backend_Server [FastAPI Host]
        WS_Out -->|PCM 16kHz Stream| WS_Gate[WebSocket Gateway]
        WS_Gate -->|Forward Audio| Gem_WS[Gemini Live API WebSocket]
        Gem_WS -->|Streaming Out PCM + Tokens| WS_Gate
        WS_Gate -->|Streaming Playback PCM| WS_In
    end

    Interrupt -->|Interrupt Signal| WS_Gate
    WS_Gate -->|Cancel Session Signal| Gem_WS
```

### Voice Pipeline Specifications
*   **Client-Side VAD**: A web assembly instance of Silero VAD runs inside the browser's audio worklet thread. It suppresses silence, ensuring only active voice frames are streamed to the backend.
*   **Streaming Protocol**: The client communicates with the FastAPI backend over a local WebSocket connection (`ws://localhost:8000/api/v1/voice/stream`). The backend proxies the connection to the Gemini Live API over an outbound WebSocket session.
*   **Interruption Handling**:
    1.  If the client VAD detects the user speaking while the assistant is playing audio, it immediately halts playback and flushes the buffer.
    2.  The client transmits a `{"type": "interrupt"}` signal over the WebSocket connection.
    3.  FastAPI receives the signal, sends a session reset/cancel command to the Gemini Live API, and updates the active conversation transcript to mark the assistant's turn as interrupted.

---

## 11. API Architecture

### WebSocket Event Protocol
All communications over `ws://localhost:8000/api/v1/voice/stream` use a structured JSON wrapper for control signals, while binary audio data is sent as raw PCM frames.

#### Client Message Types
*   **Audio Chunks**: Raw binary websocket frames containing 16kHz, 16-bit, mono PCM audio data.
*   **Control JSON Message (Telemetry Update)**:
    ```json
    {
      "type": "telemetry",
      "timestamp": "2026-06-19T12:43:40Z",
      "payload": {
        "active_file": "/src/main.c",
        "cursor_line": 42,
        "selection_empty": true,
        "compiler_error": "conflicting types for 'task_create'"
      }
    }
    ```
*   **Control JSON Message (Interruption)**:
    ```json
    {
      "type": "interrupt",
      "timestamp": "2026-06-19T12:43:42Z"
    }
    ```

#### Server Message Types
*   **Audio Output**: Raw binary websocket frames containing assistant audio chunks.
*   **Control JSON Message (Transcript Segment)**:
    ```json
    {
      "type": "transcript",
      "payload": {
        "text": "It looks like a task creation conflict. Let's check...",
        "is_final": false,
        "role": "assistant"
      }
    }
    ```
*   **Control JSON Message (System State)**:
    ```json
    {
      "type": "state",
      "payload": {
        "status": "thinking", 
        "active_skill": "FreeRTOS Expert"
      }
    }
    ```

### REST API Schema

*   `GET /api/v1/health`: Simple system health check.
*   `GET /api/v1/settings`: Fetches active personality modes, Socratic toggle states, and loaded skills.
*   `POST /api/v1/settings`: Adjusts application parameters (e.g., switching from *Mentor Mode* to *Engineer Mode*).
*   `POST /api/v1/knowledge/ingest`: Triggers a background scan and vector ingestion of the local workspace directory.
*   `GET /api/v1/memory/longterm`: Retrieves a list of saved architectural rules and developer preferences.
*   `DELETE /api/v1/memory/longterm/{id}`: Deletes or prunes a specific long-term memory entry.

---

## 12. Deployment Architecture

Taksh is structured as a **companion application** designed for simple, local installations. The database and index files are self-contained within the developer's project directory.

### Local Workspace Storage Layout

```
.taksh/                          # Project root-level configuration directory
├── taksh.db                     # Relational SQLite database
├── chroma/                      # ChromaDB storage directory
│   ├── chroma.sqlite3
│   └── index_data/
├── memory/                      # Markdown-based session logs
│   ├── session_history/
│   │   ├── session_001_log.md
│   │   └── session_002_log.md
│   └── project_memory.md        # Persistent project long-term memory rules
├── identity/
│   └── core_identity.md         # Read-only Core Identity document
├── logs/                        # Development debug log files
│   └── debug.log
└── knowledge/                   # Ingestion cache and metadata lists
    └── docs_manifest.json
```

### Installation & Execution Architecture
*   **Zero-Container Dependency**: Avoids the use of Docker for the database layer. SQLite and ChromaDB run in-process using Python bindings (`sqlite3` and `chromadb` persistent client).
*   **Local Sidecar Process**: The backend is started by running a local Python environment (`fastapi run app/main.py --port 8000`). The frontend runs in a local browser sandbox, communicating with the backend over `localhost`.
*   **Security Boundary**: The backend only listens on `127.0.0.1` interfaces, preventing unauthorized network access to the workspace and local database.

---

## 13. Future Evolution Architecture

The roadmap outlines the evolution of Taksh from a local, voice-enabled sidecar to an autonomous, cross-repository engineering companion.

```mermaid
gantt
    title Taksh Architectural Evolution Roadmap
    dateFormat  YYYY-MM
    section Version 0.1
    Local Voice Sidecar Companion   :active, 2026-06, 2026-09
    section Version 1.0
    Multi-Repository Sync & IDE Plugins : 2026-09, 2026-12
    section Version 2.0
    Fully Offline LLMs & Multimodal VAE : 2027-01, 2027-06
    section Version 3.0
    Autonomous Multi-Agent Networks & Avatars : 2027-06, 2027-12
```

### Evolutionary Roadmap Table

| Vector | Taksh v0.1 | Taksh v1.0 | Taksh v2.0 | Taksh v3.0 |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Capability** | Local voice companion sidecar; RAG for local markdown files. | IDE plugins (VS Code / JetBrains); automated file refactoring. | Fully offline voice modeling; multimodal schematic parsing. | Autonomous multi-agent networks; continuous system auditing. |
| **System Architecture** | Local FastAPI + React web UI. | IDE extension backend + headless service wrapper. | Edge-inference processing pipeline. | Multi-agent orchestrator with blackboard messaging. |
| **Memory Evolution** | In-process SQLite + ChromaDB persistence. | Shared cross-project memory databases. | Hierarchical memory networks with semantic decay. | Fully decentralized memory synchronization. |
| **Skill Evolution** | 10 static developer skills with blackboard composition. | Dynamically downloaded skills; custom DSL for user skills. | Multi-modal visual skills (PCB trace review, UI mocks). | Self-improving skills with automatic code testing. |
| **Voice & Avatar** | Single websocket PCM stream; browser playout. | Native WebRTC audio stream with server-side VAD. | Edge-to-edge voice streaming with natural pause handling. | Real-time interactive 3D visual avatar (WebGL/WebGPU). |
