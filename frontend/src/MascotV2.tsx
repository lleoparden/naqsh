import { useEffect, useRef, useState } from "react";
import mascotSvg from "../../assets/mascot/naqsh-v2.svg?raw";

export type MascotState =
  | "idle"
  | "blink"
  | "talking"
  | "thinking"
  | "curious"
  | "surprised"
  | "confused"
  | "happy"
  | "excited"
  | "laughing"
  | "proud"
  | "sad"
  | "sleepy"
  | "wave-hello"
  | "wave-goodbye"
  | "working";

const params = typeof window === "undefined" ? null : new URLSearchParams(window.location.search);

/** URL ?mascot=off or VITE_MASCOT=off disables the mascot entirely. */
export const mascotEnabled = params?.get("mascot") !== "off" && import.meta.env.VITE_MASCOT !== "off";

/**
 * Decorative mascot. aria-hidden, fixed box, never covers the canvas.
 * Hovering an idle mascot plays the one-shot hello wave.
 */
export default function Mascot({
  state = "idle",
  size = 32,
  hoverWave = false,
  className = "",
}: {
  state?: MascotState;
  size?: number;
  hoverWave?: boolean;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const [hover, setHover] = useState(false);
  const active: MascotState = hoverWave && hover && state === "idle" ? "wave-hello" : state;

  useEffect(() => {
    const svg = ref.current?.querySelector("svg");
    if (svg) svg.setAttribute("class", `mascot-v2 state-${active}`);
  }, [active]);

  if (!mascotEnabled) return null;

  return (
    <span
      ref={ref}
      aria-hidden="true"
      className={`mascot ${className}`}
      style={{ width: size, height: size, lineHeight: 0, flex: "none" }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      dangerouslySetInnerHTML={{ __html: mascotSvg }}
    />
  );
}
