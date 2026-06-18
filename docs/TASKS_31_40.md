# Tasks 31-40 — Product-Facing Vertical Slice Roadmap

This file defines the next phase after the completed backend MVP and golden PGN
corpus in `docs/TASKS_21_31.md`.

The immediate priority is not detector expansion. The current detector set is
enough for a working MVP demo:

- `HangingPieceDetector`
- `ForkDetector`
- `KnightOutpostDetector`

The next milestone is to make the system usable end to end:

```text
PGN input
-> backend analysis
-> selected coaching evidence
-> real LLM answer
-> simple UI
```

The architecture rule remains unchanged: detectors and engine verification
produce chess correctness, and the LLM explains supplied evidence only.

---

## Task 31 — Real LLM Provider Adapter

Status: planned

Dependencies:

- Task 30
- Existing `LLMClient`
- Existing `LLMPrompt`
- Existing `PromptBuilder`

Goal:

Add the first real provider implementation behind the provider-agnostic
`LLMClient` protocol.

Likely files:

```text
src/ai_chess_coach/coaching/providers/
src/ai_chess_coach/coaching/providers/openai_client.py
tests/coaching/test_openai_client.py
docs/LLM_GROUNDING.md
docs/MVP_USAGE.md
```

Recommended provider:

- OpenAI, unless a later task explicitly chooses a different provider.

Acceptance criteria:

- A concrete provider adapter exists.
- The adapter accepts `LLMPrompt`.
- The adapter preserves system/user message separation.
- API key is read from environment.
- Missing API key behavior is clear.
- Unit tests use mocks or fakes only.
- No real provider call or network access is required for tests.

Rules / non-goals:

- Do not hardcode API keys.
- Do not call detectors, replay, retrieval, Stockfish, or engine code from the
  provider adapter.
- Do not add CLI wiring yet.
- Do not add frontend, API, streaming, memory, embeddings, vector DB, or detector
  expansion.

---

## Task 32 — Backend LLM CLI Demo

Status: planned

Dependencies:

- Task 31
- Existing backend analysis CLI
- Existing `LLMChatCoach`

Goal:

Prove the complete backend plus real LLM loop from the command line.

Possible command shape:

```bash
uv run ai-chess-coach-chat game.pgn "What should I improve?"
```

Alternative, if simpler for the current CLI:

```bash
uv run ai-chess-coach-analyze game.pgn --ask "What should I improve?"
```

Expected flow:

```text
PGN
-> analysis pipeline
-> selected coaching moments/profile
-> PromptBuilder
-> provider LLMClient
-> answer
```

Acceptance criteria:

- CLI can analyze a PGN and ask a question.
- CLI uses selected coaching moments and/or retrieved/profile evidence.
- CLI does not send raw PGN as LLM evidence.
- Missing Stockfish is handled clearly.
- Missing provider API key is handled clearly.
- Tests use fake LLM clients and fake or deterministic dependencies where needed.
- Real provider calls are not required in automated tests.

Rules / non-goals:

- Do not add frontend, API server, database, auth, streaming, or detector
  expansion.

---

## Task 33 — Minimal Backend API

Status: planned

Dependencies:

- Task 32

Goal:

Add a small local-development API layer for the future frontend.

Possible endpoints:

```text
POST /analyze
POST /coach
```

Design decision to make during Task 33:

- Because there is no persistence yet, choose whether `/coach` accepts PGN plus
  question in one request or accepts structured evidence returned by `/analyze`.
- Prefer the simpler MVP option and document the tradeoff.

Acceptance criteria:

- API exposes basic PGN analysis.
- API exposes basic evidence-grounded coaching.
- API returns JSON suitable for a frontend.
- API does not expose raw internal objects directly if a simpler response DTO is
  better.
- Tests use fake LLM clients.
- No auth or persistence is added.

Rules / non-goals:

- Do not add production deployment, database, auth, frontend polish, or detector
  expansion.

---

## Task 34 — Minimal Vite React Frontend

Status: planned

Dependencies:

- Task 33

Goal:

Create a minimal frontend that proves the user-facing loop.

Core UI:

- paste or upload PGN
- click Analyze
- show selected coaching moments
- show weakness profile summary
- ask a question
- show LLM answer

Preferred stack:

- Vite React
- TypeScript unless a later task explicitly chooses JavaScript
- simple CSS

Acceptance criteria:

- User can paste PGN.
- User can run analysis.
- User can see selected coaching moments.
- User can ask a question.
- User can see an LLM answer.
- Frontend talks to the minimal backend API.
- Basic loading and error states exist.

Rules / non-goals:

- Do not add login, persistence, deployment, complex state management, or
  detector expansion.

---

## Task 35 — Board And Position Viewer

Status: planned

Dependencies:

- Task 34

Goal:

Make coaching moments visually understandable.

Features:

- display the board for a selected coaching moment
- show the position from FEN
- highlight `CoachingMoment.highlights`
- show move, SAN, and ply
- allow switching between coaching moments

Acceptance criteria:

- Board displays the relevant position.
- Highlighted squares come from backend coaching moment data.
- User can select a coaching moment and see its board.
- Viewer works with current backend output.

Rules / non-goals:

- No database, auth, advanced annotation editor, full game replay UI, or detector
  expansion unless explicitly approved in a later task.

---

## Task 36 — Product Vertical Slice Polish

Status: planned

Dependencies:

- Task 35

Goal:

Make the app demoable as a small product.

Possible improvements:

- better error messages
- sample PGNs
- prompt preview or debug mode for development
- clearer empty states
- better coaching answer formatting
- README or usage docs for the demo flow

Acceptance criteria:

- New user can run backend and frontend locally from docs.
- Demo flow is documented.
- Current limitations are clear.
- Tests still pass.

Rules / non-goals:

- No production deployment, auth, database, or detector expansion unless a later
  task explicitly changes scope.

---

## Task 37 — Detector Expansion Readiness

Status: planned after product vertical slice

Dependencies:

- Task 36
- `docs/ADDING_DETECTORS.md`

Goal:

Resume detector work only after the real LLM/API/frontend vertical slice exists.

Acceptance criteria:

- Re-read `docs/ADDING_DETECTORS.md`.
- Choose exactly one detector for the next task.
- Define event types, metadata, polarity, and verification kind before coding.
- Confirm the new detector will not weaken API/frontend/LLM grounding flow.

Rules / non-goals:

- Do not implement a detector in this readiness task.
- Do not add multiple detectors at once.

---

## Task 38 — First Post-MVP Detector

Status: planned after Task 37

Dependencies:

- Task 37

Goal:

Add one detector chosen during Task 37.

Candidate first detector:

- `LoosePieceDetector`

Rules:

- One detector only.
- Register event metadata.
- Add detector tests.
- Add verifier tests if candidate moves are introduced.
- Keep detectors deterministic, engine-free, and LLM-free.

---

## Task 39 — Second Post-MVP Detector

Status: planned after Task 38

Dependencies:

- Task 38

Goal:

Add one additional detector after the first post-MVP detector is accepted.

Candidate detector:

- `PinDetector`

Rules:

- One detector only.
- Do not bundle unrelated detector work.
- Preserve API/frontend/LLM grounding behavior.

---

## Task 40 — Third Post-MVP Detector Or Detector Infrastructure Follow-Up

Status: planned after Task 39

Dependencies:

- Task 39

Goal:

Add one more detector or a small detector infrastructure improvement discovered
while implementing Tasks 38-39.

Candidate detectors:

- `SkewerDetector`
- `BackRankWeaknessDetector`
- `PassedPawnDetector`
- pawn structure foundations

Rules:

- One focused task only.
- No detector should call Stockfish or LLMs.
- No detector should generate coaching prose.
- Do not bypass `FeatureStore` for reusable chess facts.

---

## Later

After the product vertical slice and first post-MVP detector tasks are useful,
future work may include:

- more detectors
- persistence/database for user history
- auth
- deployment
- richer board annotations
- conversation memory
- streaming LLM responses
- embeddings or vector search
