import { useEffect, useState } from "react";
import { Pipette } from "lucide-react";

const RECENT_KEY = "naqsh.recentColours";

function toHex(rgb: number[]): string {
  return `#${rgb.map((value) => Math.max(0, Math.min(255, value)).toString(16).padStart(2, "0")).join("")}`;
}

function fromHex(hex: string): number[] | null {
  const value = hex.trim().replace("#", "");
  if (!/^[0-9a-fA-F]{6}$/.test(value)) return null;
  return [0, 2, 4].map((index) => parseInt(value.slice(index, index + 2), 16));
}

/** Shared colour control: swatch picker, typed hex, recent colours, eyedropper. */
export default function ColorField({
  value,
  onChange,
  onEyedropper,
  label = "Colour",
}: {
  value: number[];
  onChange: (rgb: number[]) => void;
  onEyedropper: () => void;
  label?: string;
}) {
  const [recent, setRecent] = useState<string[]>(() => {
    try {
      return JSON.parse(window.localStorage.getItem(RECENT_KEY) || "[]") as string[];
    } catch {
      return [];
    }
  });
  const [hex, setHex] = useState(toHex(value));

  useEffect(() => setHex(toHex(value)), [value]);

  const commit = (rgb: number[]) => {
    onChange(rgb);
    const next = [toHex(rgb), ...recent.filter((item) => item !== toHex(rgb))].slice(0, 6);
    setRecent(next);
    window.localStorage.setItem(RECENT_KEY, JSON.stringify(next));
  };

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className="text-ink/70">{label}</span>
      <input
        type="color"
        aria-label={`${label} swatch`}
        value={toHex(value)}
        onChange={(event) => {
          const rgb = fromHex(event.target.value);
          if (rgb) commit(rgb);
        }}
      />
      <input
        type="text"
        aria-label={`${label} hex`}
        value={hex}
        onChange={(event) => setHex(event.target.value)}
        onBlur={() => {
          const rgb = fromHex(hex);
          if (rgb) commit(rgb);
          else setHex(toHex(value));
        }}
        className="w-24 px-1 py-1 font-mono text-[11px]"
      />
      <button
        type="button"
        aria-label="Eyedropper"
        title="Pick a colour from the page"
        className="flex h-7 w-7 items-center justify-center"
        onClick={onEyedropper}
      >
        <Pipette size={14} />
      </button>
      {recent.length > 0 && (
        <span className="flex items-center gap-1">
          {recent.map((item) => (
            <button
              key={item}
              type="button"
              aria-label={`Recent colour ${item}`}
              title={item}
              className="h-4 w-4 rounded-sm border border-border"
              style={{ background: item }}
              onClick={() => {
                const rgb = fromHex(item);
                if (rgb) onChange(rgb);
              }}
            />
          ))}
        </span>
      )}
    </div>
  );
}
