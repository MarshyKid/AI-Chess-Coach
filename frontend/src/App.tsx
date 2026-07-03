import { useEffect, useState } from "react";
import { ApiError, analyzeGame, askCoach, checkHealth } from "./api";
import type { AnalyzeResponse, ChatEntry, CoachSettings } from "./types";
import { PgnInput } from "./components/PgnInput";
import { MomentCard } from "./components/MomentCard";
import { ProfileBoard } from "./components/ProfileBoard";
import { CoachChat } from "./components/CoachChat";

export default function App() {
  const [pgn, setPgn] = useState("");
  const [analyzedPgn, setAnalyzedPgn] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const [chat, setChat] = useState<ChatEntry[]>([]);
  const [asking, setAsking] = useState(false);
  const [coachSettings, setCoachSettings] = useState<CoachSettings>({
    model: "",
    ollamaBaseUrl: "",
  });

  const [backendUp, setBackendUp] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function ping() {
      const up = await checkHealth();
      if (!cancelled) setBackendUp(up);
    }
    ping();
    const timer = setInterval(ping, 15000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  async function handleAnalyze() {
    setAnalyzing(true);
    setAnalysisError(null);
    try {
      const result = await analyzeGame(pgn);
      setAnalysis(result);
      setAnalyzedPgn(pgn);
      setChat([]);
    } catch (error) {
      setAnalysis(null);
      setAnalyzedPgn(null);
      setAnalysisError(
        error instanceof ApiError ? error.message : "Something went wrong."
      );
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleAsk(question: string) {
    if (!analyzedPgn) return;
    setAsking(true);
    setChat((entries) => [...entries, { question, answer: null, error: null }]);
    try {
      const result = await askCoach(
        analyzedPgn,
        question,
        coachSettings.model.trim() || undefined,
        coachSettings.ollamaBaseUrl.trim() || undefined
      );
      setChat((entries) =>
        entries.map((entry, index) =>
          index === entries.length - 1
            ? { ...entry, answer: result.answer }
            : entry
        )
      );
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Something went wrong.";
      setChat((entries) =>
        entries.map((entry, index) =>
          index === entries.length - 1 ? { ...entry, error: message } : entry
        )
      );
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="page">
      <header className="masthead">
        <div className="masthead__brand">
          <span className="masthead__mark">♞</span>
          <div>
            <h1>AI Chess Coach</h1>
            <p className="masthead__tag">
              Find the mistake you keep making.
            </p>
          </div>
        </div>
        <div
          className={`masthead__status ${
            backendUp === false ? "masthead__status--down" : ""
          }`}
        >
          <span className="masthead__dot" />
          {backendUp === null
            ? "Checking backend…"
            : backendUp
              ? "Backend connected"
              : "Backend offline"}
        </div>
      </header>

      <main className="content">
        <PgnInput
          pgn={pgn}
          onPgnChange={setPgn}
          onAnalyze={handleAnalyze}
          analyzing={analyzing}
        />

        {analysisError && (
          <div className="panel panel--error">
            <h2>That didn’t work</h2>
            <p>{analysisError}</p>
          </div>
        )}

        {analysis && (
          <>
            <section className="scoreline">
              <div className="scoreline__stat scoreline__stat--blue">
                <strong>{analysis.moves}</strong>
                <span>moves replayed</span>
              </div>
              <div className="scoreline__stat scoreline__stat--pink">
                <strong>{analysis.coaching_moments.length}</strong>
                <span>coaching moments</span>
              </div>
            </section>

            {analysis.coaching_moments.length > 0 && (
              <section className="panel panel--moments">
                <div className="panel__heading">
                  <h2>Coaching moments</h2>
                  <p className="panel__hint">
                    Every claim below was checked against Stockfish before it
                    reached you.
                  </p>
                </div>
                <div className="moments">
                  {analysis.coaching_moments.map((moment, index) => (
                    <MomentCard
                      key={`${moment.title}-${index}`}
                      moment={moment}
                      index={index}
                    />
                  ))}
                </div>
              </section>
            )}

            <ProfileBoard profile={analysis.weakness_profile} />
          </>
        )}

        <CoachChat
          entries={chat}
          onAsk={handleAsk}
          asking={asking}
          disabled={!analyzedPgn}
          settings={coachSettings}
          onSettingsChange={setCoachSettings}
        />
      </main>

      <footer className="footer">
        <p>
          Runs entirely on your machine — Stockfish for the truth, a local
          LLM for the words.
        </p>
      </footer>
    </div>
  );
}
