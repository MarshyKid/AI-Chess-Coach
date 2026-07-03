import type { AnalyzeResponse, CoachResponse } from "./types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function post<T>(path: string, body: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      "Could not reach the coach backend. Start it with: uvicorn ai_chess_coach.api.app:app"
    );
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      }
    } catch {
      // keep the generic message
    }
    throw new ApiError(detail);
  }

  return (await response.json()) as T;
}

export function analyzeGame(pgn: string): Promise<AnalyzeResponse> {
  return post<AnalyzeResponse>("/analyze", { pgn });
}

export function askCoach(
  pgn: string,
  question: string,
  model?: string,
  ollamaBaseUrl?: string
): Promise<CoachResponse> {
  return post<CoachResponse>("/coach", {
    pgn,
    question,
    model: model || null,
    ollama_base_url: ollamaBaseUrl || null,
  });
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
