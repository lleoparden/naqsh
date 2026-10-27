/**
 * Thin client for the Naqsh backend. The browser never talks to the model API and
 * never sees a key; everything goes through FastAPI.
 */

export type Health = {
  status: string;
  env: string;
  credential_configured: boolean;
  registers: string[];
  models: { spark: string; image: string; sam: string };
};

export type Stage = {
  name: string;
  ms: number;
  cost_usd: number;
  [key: string]: unknown;
};

export type Region = {
  id: string;
  source_text: string;
  translation_ar: string;
  style: string;
  font_style: string;
  bbox: number[];
  container: number[] | null;
  font_family: string;
  font_size: number;
  lines: string[];
};

export type Job = {
  id: string;
  register: string;
  width: number;
  height: number;
  artifacts: Record<string, string>;
  stages: Stage[];
  regions: Region[];
  warnings: string[];
  total_cost_usd: number;
  total_ms: number;
};

export async function fetchHealth(signal?: AbortSignal): Promise<Health> {
  const response = await fetch("/api/health", { signal });
  if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
  return (await response.json()) as Health;
}

export async function localize(file: File, register: string): Promise<Job> {
  const body = new FormData();
  body.append("image", file);
  body.append("register", register);
  const response = await fetch("/api/localize", { method: "POST", body });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof detail.detail === "string" ? detail.detail : `Request failed: ${response.status}`);
  }
  return (await response.json()) as Job;
}

export function artifactUrl(job: Job, name: string): string {
  const file = job.artifacts[name];
  return file ? `/api/jobs/${job.id}/files/${file}` : "";
}
