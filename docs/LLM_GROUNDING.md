# LLM Grounding

## Core Principle

The LLM explains verified evidence. It does not determine chess correctness.

Chess correctness comes from deterministic backend analysis:

```text
PGN
→ Replay
→ MoveTransition
→ FeatureStore
→ Detector
→ DetectedEvent
→ EngineAssessment
→ VerifiedEvent
→ PatternAggregation
→ WeaknessProfile
→ Retrieval/Coaching
→ LLM explains evidence only
```

## Allowed LLM Inputs

The LLM may receive structured, already selected or retrieved evidence:

- user question
- selected `CoachingMoment` objects
- retrieved `VerifiedEvent` objects
- retrieved or profile-local `DetectedPattern` objects
- `WeaknessProfile`, including high-impact strengths, execution strengths,
  weaknesses, and recurring themes

`PromptBuilder` is responsible for formatting this evidence into a grounded
`LLMPrompt`.

## Disallowed LLM Inputs

The LLM must not receive raw chess material as evidence to analyze:

- raw PGNs as evidence
- raw FENs as positions for independent analysis
- raw full-game dumps by default
- unverified tactical or positional claims
- detector-like requests such as "find the tactic" or "calculate the best move"

The user question may contain chess notation, PGN-like text, or FEN-like text.
That text remains a question. It is not treated as verified evidence, and the
prompt must still instruct the LLM not to analyze raw PGNs or FENs independently.

## Responsibilities

- Detectors identify deterministic chess events.
- Engine verification attaches objective evidence.
- Relevance, retrieval, and selection choose which evidence to show.
- `PromptBuilder` formats supplied evidence and grounding instructions.
- `LLMChatCoach` passes the prompt to an injected `LLMClient`.
- `LLMClient` adapters generate text only.

The LLM may explain, summarize, teach, and coach from supplied evidence. It may
not replace detectors, engine verification, retrieval, or selection.

## Prompt Guardrails

Grounded prompts must instruct the LLM to:

- use only supplied structured evidence
- avoid calculating moves
- avoid analyzing FENs independently
- treat FENs and position references as identifiers only
- avoid inferring material, threats, legal moves, board features, or tactics
  from a FEN
- avoid analyzing raw PGNs
- avoid inventing tactics or positional ideas not present in evidence
- avoid claiming a move is best unless supplied evidence says so
- avoid claiming there is no evidence when selected coaching moments or a
  weakness profile are supplied
- avoid asking for more game context unless no structured evidence is supplied
- base answers mainly on Coaching Moments and Weakness Profile when supplied
- state what evidence is missing when the evidence is insufficient

Mate-aware rank values are internal ordering values. They may be described as
mate-aware rank impact, but never as centipawns.

Empty optional retrieved sections do not mean evidence is absent. Selected
coaching moments and weakness profiles are primary evidence, especially for
local models that may otherwise over-focus on missing optional sections.

## Provider Clients

Real provider adapters must preserve this boundary:

- provider adapters must implement the existing `LLMClient` boundary
- provider adapters must accept `LLMPrompt`
- provider adapters must preserve separate system and user prompt content
- no raw-PGN-to-LLM shortcut
- no provider-side chess analysis
- no API key or network behavior in unit tests
- no bypassing `PromptBuilder`
- no replacing deterministic detectors or engine verification

Provider adapters should map `LLMPrompt.system` and `LLMPrompt.user` to the
provider's message format without changing the evidence contract.

## OpenAI Provider Adapter

Task 31 adds `OpenAILLMClient` under
`ai_chess_coach.coaching.providers`. It is intentionally not exported from the
top-level `ai_chess_coach.coaching` package so generic coaching imports stay
provider-neutral.

The adapter:

- accepts `LLMPrompt`
- sends `LLMPrompt.system` as OpenAI Responses API instructions
- sends `LLMPrompt.user` as the user input
- returns plain generated text from `response.output_text`
- reads API credentials from `OPENAI_API_KEY` or an explicit constructor
  argument
- reads the model from an explicit constructor argument,
  `AI_CHESS_COACH_OPENAI_MODEL`, or `DEFAULT_OPENAI_MODEL`

Install the optional SDK dependency only when using the real provider:

```bash
uv sync --extra openai
```

Unit tests use injected fake provider clients only. They must not require an API
key, provider SDK import, or network access.

Real provider integration must not broaden the LLM's responsibility: the LLM
explains selected or retrieved evidence only.

## Ollama Provider Adapter

Task 32 adds `OllamaLLMClient` under
`ai_chess_coach.coaching.providers` for no-payment local model usage. It is not
exported from the top-level `ai_chess_coach.coaching` package.

The adapter:

- accepts `LLMPrompt`
- sends `LLMPrompt.system` and `LLMPrompt.user` as separate Ollama chat messages
- calls the local `/api/chat` endpoint with `stream: false`
- returns plain generated text from `message.content`
- reads the model from an explicit constructor argument,
  `AI_CHESS_COACH_OLLAMA_MODEL`, or `DEFAULT_OLLAMA_MODEL`
- reads the base URL from an explicit constructor argument,
  `AI_CHESS_COACH_OLLAMA_BASE_URL`, or `DEFAULT_OLLAMA_BASE_URL`

Typical local setup:

```bash
ollama pull llama3.2:3b
ollama serve
```

Unit tests use injected fake transports only. They must not require Ollama to be
installed, running, or loaded with a downloaded model.

The local provider still receives only grounded prompts. It must not analyze raw
PGNs, calculate moves, call detectors, call Stockfish, or retrieve evidence.

## Ollama Chat CLI Boundary

`ai-chess-coach-chat` proves the local LLM loop from the command line. The CLI
may read raw PGN text only to run the deterministic backend analysis pipeline.
It then calls `LLMChatCoach` with selected `CoachingMoment` objects and the
`WeaknessProfile`.

The CLI must not pass raw PGN text, raw full-game dumps, or unverified chess
claims into `LLMChatCoach` or `PromptBuilder`.

Position references shown in prompts may be FEN strings, but they are labels for
grounding and UI/debugging. They are not instructions for the LLM to inspect the
board or derive new chess facts.
