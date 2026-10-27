/** Visible honesty marker for replayed jobs. Never hidden, even in ?clean=1. */
export default function DemoBadge({ source }: { source?: string }) {
  return (
    <div
      role="status"
      className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-amber-600/40 bg-amber-50 px-4 py-3 text-sm text-amber-900"
    >
      <span className="rounded bg-amber-600 px-2 py-0.5 text-xs font-semibold uppercase tracking-wider text-white">
        Demo mode
      </span>
      <span>replaying a recorded run{source ? ` — ${source}` : ""}</span>
      <span className="text-amber-800/80">
        timings and cost below are the recorded ones; this page did not call the model API
      </span>
    </div>
  );
}
