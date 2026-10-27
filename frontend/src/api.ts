/**
 * Thin client for the Naqsh backend. The browser never talks to the model API and
 * never sees a key; everything goes through FastAPI.
 */

export type Health = {
  status: string;
  env: string;
  credential_configured: boolean;
  models: { spark: string; image: string; sam: string };
};

export async function fetchHealth(signal?: AbortSignal): Promise<Health> {
  const response = await fetch("/api/health", { signal });
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  return (await response.json()) as Health;
}
