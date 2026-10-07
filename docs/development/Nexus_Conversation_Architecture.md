# Nexus Conversation & Command Architecture

This document specifies the backend conversation, session, command/response boundary, and temporary context briefing layers in Nexus Core.

---

## 1. Core Concepts

### What is a Session?
A **Session** is an in-memory, thread-safe container representing an ongoing dialogue interaction.
- Identified by a unique `session_id`.
- Stores creation and update timestamps (`created_at`, `updated_at`).
- Holds an ordered sequence of turns (`Turn`).
- Provides bounded recent context (`get_recent_turns(limit=...)`).
- Supports deterministic resets (`reset()`).
- Managed by `SessionStore`, an in-process, memory-backed registry without external database or distributed dependencies.

### What is a Turn?
A **Turn** is an immutable, typed record of a single conversational utterance.
- Roles (`TurnRole`): `USER`, `ASSISTANT`, `SYSTEM`.
- Fields: `turn_id`, `role`, `text`, `timestamp`, optional `request_id`, optional `response_id`, and `metadata`.
- Ordered chronologically inside the parent session.

### What is a Command?
A **NexusCommand** is a typed contract representing user or interface intent passed into Nexus Core.
- Fields:
  - `text`: the user input text.
  - `session_id`: optional session target (auto-generated if omitted).
  - `request_id`: unique request tracking identifier.
  - `intent`: `CommandIntent` (`CONVERSATION`, `QUERY`, `ACTION`, `SYSTEM`).
  - `preferences`: caller-provided preferences (e.g. tutor tone, conciseness).
  - `constraints`: operational constraints (e.g. "Do not write code for quizzes").
  - `evidence`: temporary caller-supplied context (e.g. note excerpts).
  - `metadata`: caller tracking metadata.

### What is a Response?
A **NexusResponse** is the typed contract returned by Nexus Core.
- Status (`ResponseStatus`): `SUCCESS`, `INVALID_REQUEST`, `MODEL_ERROR`, `INTERNAL_ERROR`.
- Fields: `request_id`, `response_id`, `session_id`, `status`, `text`, `error` (`NexusError`), `latency_ms`, `metadata`.
- Enforces strict contract invariant: successful responses contain text and no error; failure responses contain a structured `NexusError`.

### What is a Context Brief?
A **ContextBrief** is an ephemeral, immutable working context constructed solely for a single model interaction.
It aggregates:
1. Operational constraints
2. Active user/caller preferences
3. Temporary reference evidence (if provided by caller)
4. Bounded recent conversation history (excluding the current request)
5. Current user request

### What Context Brief is NOT
- Context Brief is **NOT** long-term memory.
- Context Brief is **NOT** RAG (Retrieval-Augmented Generation).
- Context Brief is **NOT** the knowledge graph.
- Context Brief is **NOT** permanent memory or note storage.
- Context Brief is **NOT** automatic retention.
Retrieval and brief-assembly do **not** imply retention. Conversation turns are not automatically dumped into knowledge files.

---

## 2. Interaction Lifecycle

```text
Caller (CLI / GUI / Web / Test)
      │
      ▼
NexusCommand
      │
      ▼
nexus_core.execute_command(command)
      │
      ▼
ConversationEngine
      ├─ 1. Validate NexusCommand
      ├─ 2. Resolve or create Session (in SessionStore)
      ├─ 3. Append User Turn (executed once)
      ├─ 4. Build ContextBrief (bounded prior turns + constraints + preferences + evidence)
      ├─ 5. Convert to ModelRequest
      ├─ 6. Execute ModelGateway.generate() with RetryPolicy
      │      └─ Transient errors (Timeout, Rate Limited, Unavailable) retried up to max_retries.
      │      └─ User turn is NOT duplicated on retry.
      ├─ 7. If ModelResult succeeds:
      │      ├─ Append Assistant Turn with response_id
      │      └─ Return NexusResponse(SUCCESS, text, latency, metadata)
      └─ 8. If ModelResult fails:
             └─ Return NexusResponse(MODEL_ERROR, error=NexusError, metadata)
```

---

## 3. Temporary vs Persistent Boundaries

| Element | Storage Mechanism | Retention Policy |
| :--- | :--- | :--- |
| **Session & Turns** | In-memory `SessionStore` | Transient (in-process lifetime; lost on restart/reset) |
| **Context Brief** | Ephemeral dataclass | Discarded immediately after model request creation |
| **Model Request / Result** | Ephemeral contract | Discarded after response construction |
| **Academic Notes & Raw Files** | Filesystem (`data/knowledge/...`) | Permanent files (authoritative source of truth) |
| **Provenance Ledger** | JSON file (`data/provenance/...`) | Permanent audit log of ingestion actions |

---

## 4. Current Limitations

1. **In-Memory Sessions**: Sessions are currently stored in memory only. Process restarts will reset active sessions.
2. **Single Model Gateway**: Uses the existing configured provider (Gemini via `ModelGateway`).
3. **No Automatic Long-term Retrieval**: The caller or high-level capability must supply reference evidence explicitly; there is no automatic background semantic search or vector retrieval.
4. **Synchronous In-Process Execution**: Commands are processed synchronously by the engine.

---

## 5. Future Extension Points

1. **File-Backed / Durable Session Storage**: Optional lightweight JSON/SQLite persistence adapter for `SessionStore` when cross-process continuity is required.
2. **Knowledge Query Capability**: Future knowledge retrieval modules can pass retrieved note citations into `NexusCommand.evidence` without polluting core logic.
3. **Multi-Modal Commands**: Extending `NexusCommand` to accept `ImageInput` and `DocumentInput` alongside text.
4. **Streaming Responses**: Supporting token-by-token streaming generator responses on the command boundary.
