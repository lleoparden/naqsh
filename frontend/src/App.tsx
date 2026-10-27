import { useEffect, useState } from "react";
import { fetchHealth, type Health } from "./api";

/**
 * Phase 1 shell. The layer editor is the product; this screen only proves the app
 * boots, speaks Arabic first, and can reach the backend.
 */
export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then(setHealth)
      .catch((err: unknown) => {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "unknown error");
      });
    return () => controller.abort();
  }, []);

  return (
    <main className="mx-auto flex min-h-full max-w-3xl flex-col justify-center gap-10 px-6 py-16">
      <header className="space-y-3">
        <p className="text-sm tracking-[0.3em] text-nile">NAQSH · نقش</p>
        <h1 className="font-arabic text-5xl leading-tight">التوطين البصري العربي، من الصورة إلى الطبقات</h1>
        <p className="max-w-xl text-lg text-ink/70">
          Arabic-first visual localization: an image becomes editable layers, translated and
          re-typeset right-to-left. The layer editor lands in Phase 2.
        </p>
      </header>

      <section className="rounded-2xl border border-sand bg-white/60 p-6">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-widest text-ink/50">
          Backend link
        </h2>
        {health ? (
          <dl className="grid gap-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-ink/60">status</dt>
              <dd>{health.status}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink/60">credential</dt>
              <dd>{health.credential_configured ? "configured" : "missing (.env)"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink/60">models</dt>
              <dd className="text-right" dir="ltr">
                {health.models.spark} · {health.models.image} · {health.models.sam}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-ink/60">
            {error ?? "Checking the backend… (start it with uvicorn app.main:app --port 8000)"}
          </p>
        )}
      </section>

      <footer className="text-xs text-ink/40">
        Meta Global AI Developer Hackathon · Build for Your World · Phase 1
      </footer>
    </main>
  );
}
