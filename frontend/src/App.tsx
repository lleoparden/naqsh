import { useCallback, useEffect, useRef, useState } from "react";
import { artifactUrl, fetchHealth, localize, type Health, type Job } from "./api";
import DemoBadge from "./DemoBadge";
import Editor from "./editor/Editor";
import { useLang } from "./i18n";
import StateIllustration from "./StateIllustration";
import Mascot from "./Mascot";

const REGISTERS = ["egyptian", "msa"] as const;

export default function App() {
  const jobParam = new URLSearchParams(window.location.search).get("job");
  if (jobParam) return <Editor jobId={jobParam} />;
  return <Home />;
}

function Home() {
  const { lang, setLang, t, stage } = useLang();
  const clean = new URLSearchParams(window.location.search).get("clean") === "1";
  const [replay, setReplay] = useState<{ index: number; done: boolean }>({ index: 0, done: true });
  const [health, setHealth] = useState<Health | null>(null);
  const [register, setRegister] = useState<string>("egyptian");
  const [backgroundLayers, setBackgroundLayers] = useState(false);
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
        setJob(await localize(file, register, backgroundLayers));
      } catch (err) {
        setError(err instanceof Error ? err.message : "unknown error");
      } finally {
        setBusy(false);
      }
    },
    [register, backgroundLayers],
  );

  useEffect(() => {
    if (!job) {
      setReplay({ index: 0, done: true });
      return;
    }
    if (!job.demo) {
      setReplay({ index: 0, done: true });
      return;
    }
    // Replay the recorded stage progress at the real recorded pace: no compression,
    // and the receipt below still shows the original total time and cost.
    const timers: number[] = [];
    let accumulated = 0;
    job.stages.forEach((item, index) => {
      accumulated += item.ms || 0;
      timers.push(
        window.setTimeout(() => {
          setReplay({ index: index + 1, done: index === job.stages.length - 1 });
        }, accumulated),
      );
    });
    setReplay({ index: 0, done: job.stages.length === 0 });
    return () => {
      timers.forEach((id) => window.clearTimeout(id));
    };
  }, [job]);

  const registerLabel = (id: string) => (id === "egyptian" ? t("registerEgyptian") : t("registerMsa"));

  return (
    <main className="mx-auto flex min-h-full max-w-5xl flex-col gap-8 px-6 py-10 text-start">
      <header className="flex flex-wrap items-start justify-between gap-6 border-b border-sand pb-6">
        <Mascot state="idle" size={44} hoverWave className="mt-1" />
        <div className="max-w-2xl">
          <p className="text-xs tracking-[0.35em] text-accent-light">{t("brand")}</p>
          <h1 className="mt-2 font-arabic text-4xl leading-tight">{t("headline")}</h1>
          <p className="mt-3 text-sm text-ink/75">{t("subhead")}</p>
        </div>

        <div className="flex flex-col items-end gap-2">
          <span className="text-xs tracking-wide text-ink/70">{t("language")}</span>
          <div className="flex overflow-hidden rounded-lg border border-sand" role="group" aria-label={t("language")}>
            {(["en", "ar"] as const).map((code) => (
              <button
                key={code}
                type="button"
                onClick={() => setLang(code)}
                aria-pressed={lang === code}
                className={`px-3 py-1.5 text-sm transition ${
                  lang === code ? "bg-nile text-white" : "bg-raised text-ink/70 hover:bg-raised"
                }`}
              >
                {code === "en" ? "EN" : "عربي"}
              </button>
            ))}
          </div>
        </div>
      </header>

      <section className="grid gap-4 rounded-2xl border border-sand bg-panel/90 p-5 sm:grid-cols-[1fr_auto]">
        <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-sand bg-paper/60 px-6 py-10 text-center transition hover:border-lacquer">
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="hidden"
            disabled={busy}
            onChange={(event) => void onFile(event.target.files?.[0])}
          />
          <span className="font-arabic text-xl">
            {busy ? t("uploadBusy", { seconds: elapsed }) : t("uploadCta")}
          </span>
          <span className="text-sm text-ink/70">{t("uploadHint")}</span>
        </label>

        <div className="flex flex-col justify-center gap-2">
          <span className="text-xs tracking-wide text-ink/70">{t("register")}</span>
          <div className="flex gap-2">
            {REGISTERS.map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => setRegister(id)}
                disabled={busy}
                aria-pressed={register === id}
                className={`rounded-lg border px-3 py-2 text-sm transition ${
                  register === id
                    ? "border-lacquer bg-lacquer text-white"
                    : "border-sand text-ink/70 hover:border-lacquer"
                }`}
              >
                {registerLabel(id)}
              </button>
            ))}
          </div>
          <p className="text-xs text-ink/70">{t("registerHint")}</p>
          <label className="mt-1 flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2 text-sm">
            <span className="flex flex-col">
              <span>{t("backgroundLayers")}</span>
              <span className="text-[11px] leading-tight text-ink/70">{t("backgroundLayersHint")}</span>
            </span>
            <input
              type="checkbox"
              role="switch"
              aria-label={t("backgroundLayers")}
              checked={backgroundLayers}
              onChange={(event) => setBackgroundLayers(event.target.checked)}
              className="h-5 w-9 accent-accent"
            />
          </label>
          {!clean && (
            <p className="text-xs text-ink/70">
              {health
                ? health.credential_configured
                  ? t("apiConfigured")
                  : t("apiMissing")
                : t("backendOffline")}
            </p>
          )}
        </div>
      </section>

      {error && (
        <StateIllustration kind="error" title="Something went wrong" detail={error} />
      )}

      {busy && !job && (
        <StateIllustration
          kind="loading"
          title="Localizing your page"
          detail="Reading the lettering, cleaning the plate and setting the Arabic. This usually takes under a minute."
        />
      )}

      {job?.demo && <DemoBadge source={job.demo_source} />}

      {job?.demo && !replay.done && (
        <section className="rounded-2xl border border-sand bg-panel/90 p-5">
          <p className="mb-2 text-xs tracking-wide text-ink/70">
            Replaying recorded stages at their real pace
          </p>
          <ul className="space-y-1 text-sm">
            {job.stages.map((item, index) => (
              <li key={item.name} className={index < replay.index ? "text-nile" : "text-ink/30"}>
                {index < replay.index ? "✓ " : "· "}
                {item.name}
                <span className="ms-2 text-xs text-ink/70">{Math.round(item.ms)} ms</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {job && !busy && (
        <StateIllustration
          compact
          kind="success"
          title="Page localized"
          detail={`${job.regions.length} regions · ${(job.total_ms / 1000).toFixed(1)} s`}
        />
      )}

      {job && (!job.demo || replay.done) && (
        <>
          <section className="grid gap-4 md:grid-cols-2">
            {/* Pixel content: never mirrored, its own LTR coordinate space. */}
            <figure dir="ltr" className="overflow-hidden rounded-2xl border border-sand bg-panel">
              <img src={artifactUrl(job, "source")} alt={t("before", { width: job.width, height: job.height })} className="w-full" />
              <figcaption className="px-4 py-2 text-xs text-ink/70">
                {t("before", { width: job.width, height: job.height })}
              </figcaption>
            </figure>
            <figure dir="ltr" className="overflow-hidden rounded-2xl border border-sand bg-panel">
              <img src={artifactUrl(job, "output")} alt={t("after", { ms: job.total_ms, cost: job.total_cost_usd.toFixed(4) })} className="w-full" />
              <figcaption className="px-4 py-2 text-xs text-ink/70">
                {t("after", { ms: job.total_ms, cost: job.total_cost_usd.toFixed(4) })}
              </figcaption>
            </figure>
          </section>

          <section className="grid gap-4 md:grid-cols-[2fr_1fr]">
            <div className="rounded-2xl border border-sand bg-panel/90 p-5">
              <h2 className="mb-3 text-sm font-semibold tracking-wide text-ink/70">
                {t("regions", { count: job.regions.length })}
              </h2>
              <ul className="space-y-2">
                {job.regions.map((region) => (
                  <li key={region.id} className="rounded-xl border border-sand/70 px-3 py-2 text-sm">
                    <div className="flex items-baseline justify-between gap-3">
                      <span dir="ltr" className="text-xs text-ink/70">
                        {region.source_text || "—"}
                      </span>
                      <span className="text-xs text-ink/70">
                        {region.font_family} · {region.font_size}px · {region.style}
                      </span>
                    </div>
                    {/* Content being localized: always Arabic and RTL, whichever UI language is on. */}
                    <p dir="rtl" lang="ar" className="font-arabic text-lg">
                      {region.translation_ar}
                    </p>
                  </li>
                ))}
              </ul>
              {job.warnings.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-semibold text-lacquer">{t("warnings")}</p>
                  <ul className="mt-1 space-y-1 text-xs text-lacquer">
                    {job.warnings.map((warning) => (
                      <li key={warning}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-sand bg-panel/90 p-5">
              <h2 className="mb-3 text-sm font-semibold tracking-wide text-ink/70">{t("receipt")}</h2>
              <dl className="space-y-1 text-xs">
                {job.stages.map((item) => (
                  <div key={item.name} className="flex justify-between gap-3">
                    <dt className="text-ink/70">{stage(item.name)}</dt>
                    <dd dir="ltr">
                      {item.ms} ms · ${item.cost_usd.toFixed(4)}
                    </dd>
                  </div>
                ))}
              </dl>
              <a
                href={artifactUrl(job, "output")}
                download={`naqsh-${job.id}.png`}
                className="me-2 mt-4 inline-block rounded-lg bg-nile px-3 py-2 text-sm text-white"
              >
                {t("download")}
              </a>
              <a
                href={`/?job=${job.id}`}
                className="ms-2 mt-4 inline-block rounded-lg bg-lacquer px-3 py-2 text-sm text-white"
              >
                Open editor
              </a>
              <a
                href={artifactUrl(job, "before_after")}
                target="_blank"
                rel="noreferrer"
                className="mt-2 block text-xs text-nile underline"
              >
                {t("sheet")}
              </a>
            </div>
          </section>
        </>
      )}

      <footer className="mt-auto border-t border-sand pt-4 text-xs text-ink/70">{t("footer")}</footer>
    </main>
  );
}
