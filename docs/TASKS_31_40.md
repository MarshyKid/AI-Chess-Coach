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
-> real or local LLM answer
-> simple UI
```

The architecture rule remains unchanged: detectors and engine verification
produce chess correctness, and the LLM explains supplied evidence only.

Provider strategy for this phase:

- Task 31 keeps the cloud OpenAI adapter available for users with API billing.
- Task 32 adds a local Ollama adapter so the MVP can run without paid cloud LLM
  tokens.
- Task 33 wires the CLI to a selectable provider.

---

## Task 31 — Real LLM Provider Adapter

Status: complete

Dependencies:

- Task 30
- Existing `LLMClient`
- Existing `LLMPrompt`
- Existing `PromptBuilder`

Goal:

Add the first real provider implementation behind the provider-agnostic
`LLMClient` protocol.

Implemented provider:

- OpenAI adapter under `ai_chess_coach.coaching.providers`

Likely files:

```text
src/ai_chess_coach/coaching/providers/
src/ai_chess_coach/coaching/providers/openai_client.py
tests/coaching/test_openai_client.py
docs/LLM_GROUNDING.md
docs/MVP_USAGE.md
```

Acceptance criteria:

- A concrete OpenAI provider adapter exists under
  `ai_chess_coach.coaching.providers`.
- The adapter accepts `LLMPrompt`.
- The adapter preserves system/user message separation through the Responses
  API.
- API key is read from `OPENAI_API_KEY` or an explicit constructor argument.
- Model is read from an explicit constructor argument,
  `AI_CHESS_COACH_OPENAI_MODEL`, or the adapter's documented
  `DEFAULT_OPENAI_MODEL`.
- Missing API key, missing optional SDK dependency, provider failure, and empty
  response behavior are clear.
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

## Task 32 — Local Ollama Provider Adapter

Status: planned

Dependencies:

- Task 31
- Existing `LLMClient`
- Existing `LLMPrompt`
- Existing provider package structure

Goal:

Add a local-model provider adapter behind the existing `LLMClient` protocol so
users can run the coaching loop without paid cloud LLM API tokens.

Recommended local provider:

- Ollama, using its local HTTP chat API.

Likely files:

```text
src/ai_chess_coach/coaching/providers/ollama_client.py
tests/coaching/test_ollama_client.py
docs/LLM_GROUNDING.md
docs/MVP_USAGE.md
docs/TASKS_31_40.md
```

Recommended adapter shape:

```python
class OllamaLLMClient:
    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        client: object | None = None,
    ) -> None: ...

    def generate(self, prompt: LLMPrompt) -> str: ...
```

Expected behavior:

- Accept `LLMPrompt`.
- Preserve separate system/user message content.
- Send a non-streaming local chat request to Ollama.
- Default base URL should be local-only, for example `http://localhost:11434`.
- Model should be configurable by constructor and environment variable.
- Use an injected fake client in tests.
- Do not require API keys.
- Do not require paid cloud tokens.
- Do not make real Ollama/network calls in automated tests.

Suggested environment variables:

```text
AI_CHESS_COACH_OLLAMA_MODEL
AI_CHESS_COACH_OLLAMA_BASE_URL
```

Suggested local setup documentation:

```bash
brew install ollama
ollama pull llama3.2:3b
ollama serve
```

Acceptance criteria:

- A concrete Ollama provider adapter exists under
  `ai_chess_coach.coaching.providers`.
- The adapter accepts `LLMPrompt`.
- The adapter maps `LLMPrompt.system` and `LLMPrompt.user` to local chat
  messages.
- The adapter requests non-streaming output for MVP simplicity.
- Local model and base URL configuration are clear.
- Ollama unavailable / connection failure behavior is clear.
- Missing model or empty response behavior is clear.
- Unit tests use fake/mocked clients only.
- No real local server, network call, or model download is required for tests.
- No detector, engine, replay, retrieval, PromptBuilder, or LLMChatCoach logic is
  called by the provider adapter.

Rules / non-goals:

- Do not add CLI wiring yet; that is Task 33.
- Do not add frontend or API work.
- Do not add streaming.
- Do not add memory or embeddings.
- Do not add detector expansion.
- Do not require Ollama in the automated test suite.
- Prefer standard-library HTTP or a very small optional dependency; do not add a
  heavy framework for this adapter.

---

## Task 33 — Backend LLM CLI Demo

Status: planned

Dependencies:

- Task 31
- Task 32
- Existing backend analysis CLI
- Existing `LLMChatCoach`

Goal:

Prove the complete backend plus LLM loop from the command line, with a selectable
provider.

Possible command shape:

```bash
uv run ai-chess-coach-chat game.pgn "What should I improve?" --provider ollama
```

Alternative, if simpler for the current CLI:

```bash
uv run ai-chess-coach-analyze game.pgn --ask "What should I improve?" --provider ollama
```

Provider options:

- `ollama` should be the recommended no-payment local default.
- `openai` should remain available for users with API billing.

Expected flow:

```text
PGN
-> analysis pipeline
-> selected coaching moments/profile
-> PromptBuilder
-> selected LLMClient provider
-> answer
```

Acceptance criteria:

- CLI can analyze a PGN and ask a question.
- CLI can use the Ollama provider for local no-token demos.
- CLI can use the OpenAI provider when configured.
- CLI uses selected coaching moments and/or retrieved/profile evidence.
- CLI does not send raw PGN as LLM evidence.
- Missing Stockfish is handled clearly.
- Missing or unavailable LLM provider is handled clearly.
- Missing OpenAI API key is handled clearly when `--provider openai` is selected.
- Missing local Ollama server/model is handled clearly when `--provider ollama`
  is selected.
- Tests use fake LLM clients and fake or deterministic dependencies where needed.
- Real provider calls are not required in automated tests.

Rules / non-goals:

- Do not add frontend, API server, database, auth, streaming, or detector
  expansion.

---

## Task 34 — Minimal Backend API

Status: planned

Dependencies:

- Task 33

Goal:

Add a small local-development API layer for the future frontend.

Possible endpoints:

```text
POST /analyze
POST /coach
```

Design decision to make during Task 34:

- Because there is no persistence yet, choose whether `/coach` accepts PGN plus
  question in one request or accepts structured evidence returned by `/analyze`.
- Prefer the simpler MVP option and document the tradeoff.
- Decide how provider selection should work locally, for example `ollama` by
  default and `openai` by explicit configuration.

Acceptance criteria:

- API exposes basic PGN analysis.
- API exposes basic evidence-grounded coaching.
- API returns JSON suitable for a frontend.
- API can use fake LLM clients in tests.
- API does not expose raw internal objects directly if a simpler response DTO is
  better.
- No auth or persistence is added.

Rules / non-goals:

- Do not add production deployment, database, auth, frontend polish, or detector
  expansion.

---

## Task 35 — Minimal Vite React Frontend

Status: planned

Dependencies:

- Task 34

Goal:

Create a minimal frontend that proves the user-facing loop.

Core UI:

- paste or upload PGN
- click Analyze
- show selected coaching moments
- show weakness profile summary
- ask a question
- choose or display the configured provider, if useful
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

## Task 36 — Board And Position Viewer

Status: planned

Dependencies:

- Task 35

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

## Task 37 — Product Vertical Slice Polish

Status: planned

Dependencies:

- Task 36

Goal:

Make the app demoable as a small local product.

Possible improvements:

- better error messages
- sample PGNs
- prompt preview or debug mode for development
- clearer empty states
- better coaching answer formatting
- provider setup help for Ollama and OpenAI
- README or usage docs for the demo flow

Acceptance criteria:

- New user can run backend and frontend locally from docs.
- Demo flow is documented.
- No-payment local Ollama demo flow is documented.
- Optional OpenAI demo flow is documented.
- Current limitations are clear.
- Tests still pass.

Rules / non-goals:

- No production deployment, auth, database, or detector expansion unless a later
  task explicitly changes scope.

---

## Task 38 — Detector Expansion Readiness

Status: planned after product vertical slice

Dependencies:

- Task 37
- `docs/ADDING_DETECTORS.md`

Goal:

Resume detector work only after the real/local LLM, API, and frontend vertical
slice exists.

Acceptance criteria:

- Re-read `docs/ADDING_DETECTORS.md`.
- Choose exactly one detector for the next task.
- Define event types, metadata, polarity, and verification kind before coding.
- Confirm the new detector will not weaken API/frontend/LLM grounding flow.

Rules / non-goals:

- Do not implement a detector in this readiness task.
- Do not add multiple detectors at once.

---

## Task 39 — First Post-MVP Detector

Status: planned after Task 38

Dependencies:

- Task 38

Goal:

Add one detector chosen during Task 38.

Candidate first detector:

- `LoosePieceDetector`

Rules:

- One detector only.
- Register event metadata.
- Add detector tests.
- Add verifier tests if candidate moves are introduced.
- Keep detectors deterministic, engine-free, and LLM-free.

---

## Task 40 — Second Post-MVP Detector Or Detector Infrastructure Follow-Up

Status: planned after Task 39

Dependencies:

- Task 39

Goal:

Add one additional detector or a small detector infrastructure improvement
discovered while implementing Tasks 38-39.

Candidate detectors:

- `PinDetector`
- `SkewerDetector`
- `BackRankWeaknessDetector`
- `PassedPawnDetector`
- pawn structure foundations

Rules:

- One focused task only.
- Do not bundle unrelated detector work.
- Preserve API/frontend/LLM grounding behavior.
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
