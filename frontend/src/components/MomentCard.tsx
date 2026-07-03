import { useEffect, useState } from "react";
import type { CoachingMomentSummary } from "../types";
import { ChessBoard } from "./ChessBoard";

interface MomentCardProps {
  moment: CoachingMomentSummary;
  index: number;
}

export function MomentCard({ moment, index }: MomentCardProps) {
  const [showEvidence, setShowEvidence] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!expanded) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setExpanded(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [expanded]);

  return (
    <article className="moment">
      <div className="moment__body">
        <span className="moment__number">{index + 1}</span>
        <h3 className="moment__title">{moment.title}</h3>
        <p className="moment__explanation">{moment.explanation}</p>

        {moment.details.length > 0 && (
          <div className="moment__evidence">
            <button
              className="btn btn--tiny"
              onClick={() => setShowEvidence((open) => !open)}
            >
              {showEvidence ? "Hide engine evidence" : "Engine evidence"}
            </button>
            {showEvidence && (
              <ul className="moment__details">
                {moment.details.map((detail) => (
                  <li key={detail}>{detail}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {moment.position_reference && (
        <div className="moment__board">
          <ChessBoard
            fen={moment.position_reference}
            highlights={moment.highlights}
          />
          {moment.highlights.length > 0 && (
            <p className="moment__squares">
              Watch {moment.highlights.join(", ")}
            </p>
          )}
          <button
            className="btn btn--tiny moment__expand"
            onClick={() => setExpanded(true)}
          >
            Expand board
          </button>

          {expanded && (
            <div
              className="board-modal"
              onClick={() => setExpanded(false)}
              role="dialog"
              aria-modal="true"
              aria-label={`Position for ${moment.title}`}
            >
              <div
                className="board-modal__card"
                onClick={(event) => event.stopPropagation()}
              >
                <div className="board-modal__top">
                  <h3>{moment.title}</h3>
                  <button
                    className="btn btn--tiny"
                    onClick={() => setExpanded(false)}
                    aria-label="Close expanded board"
                  >
                    ✕ Close
                  </button>
                </div>
                <ChessBoard
                  fen={moment.position_reference}
                  highlights={moment.highlights}
                />
                {moment.highlights.length > 0 && (
                  <p className="moment__squares">
                    Watch {moment.highlights.join(", ")}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </article>
  );
}
