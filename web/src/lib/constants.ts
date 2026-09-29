export const DEFAULT_BACKEND = "http://127.0.0.1:8000";

export const SOURCE_TIER_LABELS: Record<number, string> = {
  1: "Tier 1 — Regulatory filing",
  2: "Tier 2 — Regulator / tribunal",
  3: "Tier 3 — Audited report",
  4: "Tier 4 — Company PR",
  5: "Tier 5 — News",
};

export const VERDICT_COLORS: Record<string, string> = {
  ALIGN: "#1a7f37",
  CONTRADICT: "#b42318",
  INSUFFICIENT_EVIDENCE: "#946800",
  NOT_APPLICABLE: "#6b7280",
};

export const VERDICT_BG: Record<string, string> = {
  ALIGN: "#e6f4ea",
  CONTRADICT: "#fbeae8",
  INSUFFICIENT_EVIDENCE: "#fdf3e0",
  NOT_APPLICABLE: "#eef0f2",
};
