/** Visible honesty marker for replayed jobs. Never hidden, even in ?clean=1. */
export default function DemoBadge({ source }: { source?: string }) {
  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-accent/40 bg-accent/10 px-4 py-3 text-sm text-fg"
    >
      <span className="rounded bg-accent px-2 py-0.5 text-xs font-semibold  text-white">
        Demo mode
      </span>
      <span>replaying a recorded run{source ? ` — ${source}` : ""}</span>
      <span className="text-muted">
        timings and cost below are the recorded ones; this page did not call the model API
      </span>
    </div>
  );
}
