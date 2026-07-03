# AI Chess Coach — Frontend

React + Vite + TypeScript client for the local FastAPI backend. All chess
intelligence stays in the backend; this app only renders verified evidence
and relays coach questions.

## Run

Start the backend from the repository root (requires Stockfish on `PATH`
or `STOCKFISH_PATH`):

```bash
uv run uvicorn ai_chess_coach.api.app:app --port 8000
```

Then start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The backend's CORS config expects the dev
server on port 5173.

## Configuration

- `VITE_API_BASE_URL` — backend base URL, defaults to `http://127.0.0.1:8000`.
- Ollama model and base URL for the "Ask the coach" panel can be set in
  the UI under "Ollama settings".

## Build

```bash
npm run build
```

Output lands in `frontend/dist/`.
