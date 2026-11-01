import type { ReactNode } from "react";
import Mascot from "./Mascot";

/**
 * One state illustration for loading, empty, success and error.
 *
 * Single icon slot (a placeholder for the future brand illustration) and a single
 * content slot, so the visual can be swapped in one place later without touching every
 * screen. Do not add per-screen icons for these states.
 */
export default function StateIllustration({
  kind,
  title,
  detail,
  children,
  compact = false,
}: {
  kind: "loading" | "empty" | "success" | "error";
  title: string;
  detail?: string;
  children?: ReactNode;
  compact?: boolean;
}) {
  const tone =
    kind === "error"
      ? "border-danger/40 bg-danger/5"
      : kind === "success"
        ? "border-success/40 bg-success/5"
        : "border-border bg-panel";
  const size = compact ? "px-4 py-3" : "px-6 py-8";
  const iconBox = compact ? "h-8 w-8" : "h-12 w-12";
  const mascotState =
    kind === "loading" ? "thinking" : kind === "success" ? "happy" : kind === "error" ? "sad" : "idle";
  return (
    <section role="status" className={`rounded-xl border ${tone} ${size} text-center`}>
      <div className={`mx-auto flex ${iconBox} items-center justify-center rounded-full border border-border bg-raised text-ink/70`}>
        <Mascot state={mascotState} size={compact ? 24 : 36} />
      </div>
      <h3 className="mt-3 text-sm font-semibold text-fg">{title}</h3>
      {detail && <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-ink/70">{detail}</p>}
      {children && <div className="mt-4 flex justify-center">{children}</div>}
    </section>
  );
}
