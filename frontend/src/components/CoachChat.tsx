import { useState } from "react";
import type { ChatEntry, CoachSettings } from "../types";

const SUGGESTED_QUESTIONS = [
  "What should I work on first?",
  "Why did I lose material?",
  "Which of my moves was the biggest mistake?",
];

interface CoachChatProps {
  entries: ChatEntry[];
  onAsk: (question: string) => void;
  asking: boolean;
  disabled: boolean;
  settings: CoachSettings;
  onSettingsChange: (settings: CoachSettings) => void;
}

export function CoachChat({
  entries,
  onAsk,
  asking,
  disabled,
  settings,
  onSettingsChange,
}: CoachChatProps) {
  const [question, setQuestion] = useState("");

  function submit(text: string) {
    const trimmed = text.trim();
    if (!trimmed || asking || disabled) return;
    onAsk(trimmed);
    setQuestion("");
  }

  return (
    <section className="panel panel--coach">
      <div className="panel__heading">
        <h2>Ask the coach</h2>
        <p className="panel__hint">
          Answers stick to the verified evidence above — no engine-speak,
          no made-up lines.
        </p>
      </div>

      {disabled && (
        <p className="coach__locked">Analyze a game first, then ask away.</p>
      )}

      {entries.length > 0 && (
        <div className="coach__thread">
          {entries.map((entry, index) => (
            <div key={index} className="coach__exchange">
              <p className="coach__question">{entry.question}</p>
              {entry.answer !== null && (
                <p className="coach__answer">{entry.answer}</p>
              )}
              {entry.error !== null && (
                <p className="coach__error">{entry.error}</p>
              )}
              {entry.answer === null && entry.error === null && (
                <p className="coach__answer coach__answer--pending">
                  Thinking it over…
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {!disabled && entries.length === 0 && (
        <div className="coach__suggestions">
          {SUGGESTED_QUESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              className="btn btn--tiny"
              onClick={() => submit(suggestion)}
              disabled={asking}
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}

      <form
        className="coach__form"
        onSubmit={(event) => {
          event.preventDefault();
          submit(question);
        }}
      >
        <input
          className="coach__input"
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about this game…"
          disabled={disabled || asking}
        />
        <button
          className="btn btn--primary"
          type="submit"
          disabled={disabled || asking || !question.trim()}
        >
          {asking ? "Thinking…" : "Ask"}
        </button>
      </form>

      <details className="coach__settings">
        <summary>Ollama settings</summary>
        <div className="coach__settings-fields">
          <label>
            Model
            <input
              type="text"
              value={settings.model}
              placeholder="default"
              onChange={(event) =>
                onSettingsChange({ ...settings, model: event.target.value })
              }
            />
          </label>
          <label>
            Base URL
            <input
              type="text"
              value={settings.ollamaBaseUrl}
              placeholder="http://localhost:11434"
              onChange={(event) =>
                onSettingsChange({
                  ...settings,
                  ollamaBaseUrl: event.target.value,
                })
              }
            />
          </label>
        </div>
      </details>
    </section>
  );
}
