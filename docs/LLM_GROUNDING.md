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
- avoid analyzing raw PGNs
- avoid inventing tactics or positional ideas not present in evidence
- avoid claiming a move is best unless supplied evidence says so
- state what evidence is missing when the evidence is insufficient

Mate-aware rank values are internal ordering values. They may be described as
mate-aware rank impact, but never as centipawns.

## Future Provider Clients

Real Anthropic, OpenAI, Gemini, or other provider adapters must preserve this
boundary:

- no raw-PGN-to-LLM shortcut
- no provider-side chess analysis
- no API key or network behavior in unit tests
- no bypassing `PromptBuilder`
- no replacing deterministic detectors or engine verification

Provider adapters should map `LLMPrompt.system` and `LLMPrompt.user` to the
provider's message format without changing the evidence contract.
