// Thin fetch helpers for the v2 backend. No business logic here.
import { createContext, useContext } from "react";
import { DEFAULT_BACKEND } from "./constants";

export class HttpError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const KEY = "esg.backendUrl";

export function loadBackendUrl(): string {
  try {
    return localStorage.getItem(KEY) || DEFAULT_BACKEND;
  } catch {
    return DEFAULT_BACKEND;
  }
}

export function saveBackendUrl(url: string) {
  try {
    localStorage.setItem(KEY, url);
  } catch {
    /* storage unavailable, ignore */
  }
}

export const BackendContext = createContext<string>(DEFAULT_BACKEND);
export const useBackend = () => useContext(BackendContext);

export function url(base: string, path: string): string {
  return `${base.replace(/\/+$/, "")}${path}`;
}

async function detail(res: Response): Promise<string> {
  try {
    const b = await res.json();
    if (typeof b.detail === "string") return b.detail;
    return JSON.stringify(b.detail ?? b);
  } catch {
    return res.statusText || `HTTP ${res.status}`;
  }
}

export async function getJson<T>(base: string, path: string, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url(base, path), { signal });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new HttpError(0, `Cannot reach backend at ${base}`);
  }
  if (!res.ok) throw new HttpError(res.status, await detail(res));
  return res.json() as Promise<T>;
}

export async function startAnalysis(
  base: string,
  opts: { demoReport?: string; file?: File | null; maxClaims?: number },
): Promise<{ analysis_id: string; status: string }> {
  const form = new FormData();
  if (opts.file) form.append("file", opts.file);
  else if (opts.demoReport) form.append("demo_report", opts.demoReport);
  if (opts.maxClaims) form.append("max_claims", String(opts.maxClaims));
  let res: Response;
  try {
    res = await fetch(url(base, "/v2/analyses"), { method: "POST", body: form });
  } catch {
    throw new HttpError(0, `Cannot reach backend at ${base}`);
  }
  if (!res.ok) throw new HttpError(res.status, await detail(res));
  return res.json();
}

export async function postJson<T>(base: string, path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url(base, path), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new HttpError(0, `Cannot reach backend at ${base}`);
  }
  if (!res.ok) throw new HttpError(res.status, await detail(res));
  return res.json() as Promise<T>;
}
