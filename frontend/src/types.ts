export interface CoachingMomentSummary {
  title: string;
  explanation: string;
  position_reference: string | null;
  highlights: string[];
  details: string[];
}

export interface PatternSummary {
  pattern_type: string;
  display_name: string;
  frequency: number;
  severity: number;
}

export interface WeaknessProfileSummary {
  strengths: PatternSummary[];
  execution_strengths: PatternSummary[];
  weaknesses: PatternSummary[];
  recurring_themes: PatternSummary[];
}

export interface AnalyzeResponse {
  moves: number;
  coaching_moments: CoachingMomentSummary[];
  weakness_profile: WeaknessProfileSummary;
}

export interface EvidenceSummary {
  coaching_moment_count: number;
  has_weakness_profile: boolean;
}

export interface CoachResponse {
  answer: string;
  evidence_summary: EvidenceSummary;
  coaching_moments: CoachingMomentSummary[];
  weakness_profile: WeaknessProfileSummary;
}

export interface CoachSettings {
  model: string;
  ollamaBaseUrl: string;
}

export interface ChatEntry {
  question: string;
  answer: string | null;
  error: string | null;
}
