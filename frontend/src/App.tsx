import { useCallback, useEffect, useRef, useState } from "react";
import { artifactUrl, fetchHealth, localize, type Health, type Job } from "./api";

const REGISTERS: { id: string; label: string; hint: string }[] = [
  { id: "egyptian", label: "عامية مصرية", hint: "Egyptian colloquial" },
  { id: "msa", label: "الفصحى", hint: "Modern Standard Arabic" },
];

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [register, setRegister] = useState("egyptian");
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetchHealth(controller.signal)
      .then(setHealth)
      .catch(() => setHealth(null));
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!busy) {
      if (timer.current) window.clearInterval(timer.current);
      timer.current = null;
      return;
    }
    const started = Date.now();
    setElapsed(0);
    timer.current = window.setInterval(() => setElapsed(Math.round((Date.now() - started) / 1000)), 250);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [busy]);

  const onFile = useCallback(
    async (file: File | undefined) => {
      if (!file) return;
      setError(null);
      setJob(null);
      setBusy(true);
      try {
        setJob(await localize(file, register));
      } catch (err) {
        setError(err instanceof Error ? err.message : "unknown error");
      } finally {
        setBusy(false);
      }
    },
    [register],
  );

  return (
    <main className="mx-auto flex min-h-full max-w-5xl flex-col gap-8 px-6 py-10">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-sand pb-6">
        <div>
          <p className="text-xs tracking-[0.35em] text-nile">NAQSH · نقش</p>
          <h1 className="mt-2 font-arabic text-4xl leading-tight">حوّل أي صورة إلى طبقات عربية قابلة للتعديل</h1>
        </div>
        <p className="max-w-xs text-sm text-ink/60">
          Arabic-first localization: readers find the lettering, the plate is repainted, and the
          Arabic is set right-to-left in the original space.
        </p>
      </header>

      <section className="grid gap-4 rounded-2xl border border-sand bg-white/70 p-5 sm:grid-cols-[1fr_auto]">
        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-sand bg-paper/60 px-6 py-10 text-center transition hover:border-lacquer">
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            disabled={busy}
            onChange={(event) => void onFile(event.target.files?.[0])}
          />
          <span className="font-arabic text-xl">{busy ? "جارٍ العمل…" : "اختر صفحة لتعريبها"}</span>
          <span className="text-sm text-ink/50">
            {busy ? `${elapsed}s — reading, segmenting, repainting, typesetting` : "PNG, JPEG or WebP · up to 15 MB"}
          </span>
        </label>

        <div className="flex flex-col justify-center gap-2">
          <span className="text-xs uppercase tracking-widest text-ink/40">Register</span>
          <div className="flex gap-2">
            {REGISTERS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setRegister(item.id)}
                disabled={busy}
                className={`rounded-lg border px-3 py-2 text-sm transition ${
                  register === item.id
                    ? "border-lacquer bg-lacquer text-paper"
                    : "border-sand text-ink/70 hover:border-lacquer"
                }`}
                title={item.hint}
              >
                <span className="font-arabic">{item.label}</span>
              </button>
            ))}
          </div>
          <p className="text-xs text-ink/40">
            {health ? (health.credential_configured ? "API key configured" : "API key missing in .env") : "backend offline"}
          </p>
        </div>
      </section>

      {error && (
        <p className="rounded-xl border border-lacquer/30 bg-lacquer/5 px-4 py-3 text-sm text-lacquer">{error}</p>
      )}

      {job && (
        <>
          <section className="grid gap-4 md:grid-cols-2">
            <figure className="overflow-hidden rounded-2xl border border-sand bg-white">
              <img src={artifactUrl(job, "source")} alt="Source page" className="w-full" />
              <figcaption className="px-4 py-2 text-xs text-ink/50">Before · {job.width}×{job.height}</figcaption>
            </figure>
            <figure className="overflow-hidden rounded-2xl border border-sand bg-white">
              <img src={artifactUrl(job, "output")} alt="Localized page" className="w-full" />
              <figcaption className="px-4 py-2 text-xs text-ink/50">
                After · {job.total_ms} ms · ${job.total_cost_usd.toFixed(4)}
              </figcaption>
            </figure>
          </section>

          <section className="grid gap-4 md:grid-cols-[2fr_1fr]">
            <div className="rounded-2xl border border-sand bg-white/70 p-5">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-ink/50">
                Regions · {job.regions.length}
              </h2>
              <ul className="space-y-2">
                {job.regions.map((region) => (
                  <li key={region.id} className="rounded-xl border border-sand/70 px-3 py-2 text-sm">
                    <div className="flex items-baseline justify-between gap-3">
                      <span dir="ltr" className="text-xs text-ink/40">
                        {region.source_text || "—"}
                      </span>
                      <span className="text-xs text-ink/40">
                        {region.font_family} · {region.font_size}px · {region.style}
                      </span>
                    </div>
                    <p className="font-arabic text-lg">{region.translation_ar}</p>
                  </li>
                ))}
              </ul>
              {job.warnings.length > 0 && (
                <ul className="mt-3 space-y-1 text-xs text-lacquer">
                  {job.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              )}
            </div>

            <div className="rounded-2xl border border-sand bg-white/70 p-5">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-widest text-ink/50">Receipt</h2>
              <dl className="space-y-1 text-xs">
                {job.stages.map((stage) => (
                  <div key={stage.name} className="flex justify-between gap-3">
                    <dt className="text-ink/50">{stage.name}</dt>
                    <dd dir="ltr">
                      {stage.ms} ms · ${stage.cost_usd.toFixed(4)}
                    </dd>
                  </div>
                ))}
              </dl>
              <a
                href={artifactUrl(job, "output")}
                download={`naqsh-${job.id}.png`}
                className="mt-4 inline-block rounded-lg bg-nile px-3 py-2 text-sm text-paper"
              >
                Download PNG
              </a>
              <a
                href={artifactUrl(job, "before_after")}
                target="_blank"
                rel="noreferrer"
                className="mt-2 block text-xs text-nile underline"
              >
                Before / after sheet
              </a>
            </div>
          </section>
        </>
      )}

      <footer className="mt-auto border-t border-sand pt-4 text-xs text-ink/40">
        Meta Global AI Developer Hackathon · Build for Your World · Phase 2 vertical slice
      </footer>
    </main>
  );
}
