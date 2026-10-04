// Thin fetch wrapper around the FastAPI backend (app/api/main.py). This file
// contains NO business logic -- it only sends requests and surfaces the
// backend's own error messages. Any failure is thrown, never swallowed into
// a fake success.

import type { AnalyzeResult } from "./types";

export class ApiError extends Error {}

export interface AnalyzeParams {
  file?: File | null;
  useDemo: boolean;
  company?: string;
  mode: string;
  topK: number;
  useSemantic: boolean;
}

async function parseErrorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    return body.detail ?? res.statusText;
  } catch {
    return res.statusText || `HTTP ${res.status}`;
  }
}

export async function checkHealth(backendUrl: string): Promise<boolean> {
  try {
    const res = await fetch(`${backendUrl}/health`, { signal: AbortSignal.timeout(5000) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function analyze(backendUrl: string, params: AnalyzeParams): Promise<AnalyzeResult> {
  const form = new FormData();
  form.append("use_demo", String(params.useDemo));
  form.append("company", params.company ?? "");
  form.append("mode", params.mode);
  form.append("top_k", String(params.topK));
  form.append("use_semantic", String(params.useSemantic));
  if (params.file) {
    form.append("file", params.file);
  }

  const res = await fetch(`${backendUrl}/analyze`, { method: "POST", body: form });
  if (!res.ok) {
    throw new ApiError(await parseErrorDetail(res));
  }
  return res.json();
}

export async function demoDataset(
  backendUrl: string,
  topK: number,
  useSemantic: boolean,
): Promise<AnalyzeResult> {
  const url = new URL(`${backendUrl}/demo/dataset`);
  url.searchParams.set("top_k", String(topK));
  url.searchParams.set("use_semantic", String(useSemantic));

  const res = await fetch(url.toString());
  if (!res.ok) {
    throw new ApiError(await parseErrorDetail(res));
  }
  return res.json();
}
