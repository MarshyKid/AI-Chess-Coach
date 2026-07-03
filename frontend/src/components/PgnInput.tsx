import { useRef, useState } from "react";

// Morphy vs. Duke Karl / Count Isouard, Paris Opera 1858.
const SAMPLE_PGN = `[Event "Paris Opera"]
[Site "Paris FRA"]
[Date "1858.11.02"]
[White "Paul Morphy"]
[Black "Duke Karl / Count Isouard"]
[Result "1-0"]

1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7
8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8 13. Rxd7 Rxd7
14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0`;

interface PgnInputProps {
  pgn: string;
  onPgnChange: (pgn: string) => void;
  onAnalyze: () => void;
  analyzing: boolean;
}

export function PgnInput({ pgn, onPgnChange, onAnalyze, analyzing }: PgnInputProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    const text = await file.text();
    onPgnChange(text);
    setFileName(file.name);
  }

  return (
    <section className="panel panel--input">
      <div className="panel__heading">
        <h2>Your game</h2>
        <p className="panel__hint">
          Paste a PGN, or load one from Lichess or Chess.com exports.
        </p>
      </div>

      <textarea
        className="pgn-box"
        value={pgn}
        onChange={(event) => {
          onPgnChange(event.target.value);
          setFileName(null);
        }}
        placeholder={'1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 ...'}
        spellCheck={false}
        rows={9}
      />

      <div className="panel__actions">
        <button
          className="btn btn--primary"
          onClick={onAnalyze}
          disabled={analyzing || !pgn.trim()}
        >
          {analyzing ? "Analyzing…" : "Analyze game"}
        </button>
        <button
          className="btn btn--plain"
          onClick={() => fileInputRef.current?.click()}
          disabled={analyzing}
        >
          {fileName ? `Loaded ${fileName}` : "Open .pgn file"}
        </button>
        <button
          className="btn btn--plain"
          onClick={() => {
            onPgnChange(SAMPLE_PGN);
            setFileName(null);
          }}
          disabled={analyzing}
        >
          Try the Opera Game
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pgn,text/plain"
          hidden
          onChange={(event) => handleFile(event.target.files?.[0])}
        />
      </div>
    </section>
  );
}
