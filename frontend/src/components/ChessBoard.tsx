import { Piece, isPieceChar } from "./pieces";

const FILES = ["a", "b", "c", "d", "e", "f", "g", "h"];

interface SquareInfo {
  name: string;
  piece: string | null;
  isDark: boolean;
}

/**
 * Expand a FEN piece-placement field into 64 squares, a8 first.
 * Display only — the backend owns every chess judgement.
 */
function readBoard(fen: string): SquareInfo[] | null {
  const placement = fen.trim().split(/\s+/)[0];
  if (!placement) return null;

  const ranks = placement.split("/");
  if (ranks.length !== 8) return null;

  const squares: SquareInfo[] = [];
  for (let rankIndex = 0; rankIndex < 8; rankIndex++) {
    const rank = ranks[rankIndex];
    let fileIndex = 0;
    for (const char of rank) {
      if (/[1-8]/.test(char)) {
        const emptyCount = Number(char);
        for (let i = 0; i < emptyCount; i++) {
          squares.push(makeSquare(fileIndex, rankIndex, null));
          fileIndex++;
        }
      } else if (isPieceChar(char)) {
        squares.push(makeSquare(fileIndex, rankIndex, char));
        fileIndex++;
      } else {
        return null;
      }
    }
    if (fileIndex !== 8) return null;
  }

  return squares;
}

function makeSquare(
  fileIndex: number,
  rankIndex: number,
  piece: string | null
): SquareInfo {
  return {
    name: `${FILES[fileIndex]}${8 - rankIndex}`,
    piece,
    isDark: (fileIndex + rankIndex) % 2 === 1,
  };
}

interface ChessBoardProps {
  fen: string;
  highlights: string[];
}

export function ChessBoard({ fen, highlights }: ChessBoardProps) {
  const squares = readBoard(fen);
  if (!squares) return null;

  const highlighted = new Set(highlights);

  return (
    <div className="board" role="img" aria-label={`Chess position ${fen}`}>
      {squares.map((square) => {
        const classes = ["board__square"];
        classes.push(square.isDark ? "board__square--dark" : "board__square--light");
        if (highlighted.has(square.name)) classes.push("board__square--hot");

        return (
          <div key={square.name} className={classes.join(" ")}>
            {square.piece && <Piece piece={square.piece} />}
            {square.name[0] === "a" && (
              <span className="board__rank-label">{square.name[1]}</span>
            )}
            {square.name[1] === "1" && (
              <span className="board__file-label">{square.name[0]}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
