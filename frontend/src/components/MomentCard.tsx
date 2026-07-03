import { useState } from "react";
import type { CoachingMomentSummary } from "../types";
import { ChessBoard } from "./ChessBoard";

interface MomentCardProps {
  moment: CoachingMomentSummary;
  index: number;
}

export function MomentCard({ moment, index }: MomentCardProps) {
  const [showEvidence, setShowEvidence] = useState(false);

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
        </div>
      )}
    </article>
  );
}
