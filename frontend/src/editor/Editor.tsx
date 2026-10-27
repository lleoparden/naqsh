import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import DemoBadge from "../DemoBadge";
import { layerById, FONTS, FONT_LABELS, type Document, type Layer } from "./types";
import { useEditor } from "./useEditor";

type DragState =
  | { mode: "pan"; startX: number; startY: number; originX: number; originY: number }
  | { mode: "move"; layerId: string; startX: number; startY: number; box: [number, number, number, number]; snapshot: Document }
  | { mode: "resize"; layerId: string; startX: number; startY: number; box: [number, number, number, number]; snapshot: Document }
  | { mode: "cover"; startX: number; startY: number; currentX: number; currentY: number }
  | null;

export default function Editor({ jobId }: { jobId: string }) {
  const editor = useEditor(jobId);
  const doc = editor.document;
  const [selected, setSelected] = useState<string | null>(null);
  const [zoom, setZoom] = useState(0.55);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [tool, setTool] = useState<"select" | "cover">("select");
  const [showOriginal, setShowOriginal] = useState(false);
  const [split, setSplit] = useState(100);
  const [draft, setDraft] = useState<DragState>(null);
  const [retranslateCost, setRetranslateCost] = useState<number | null>(null);
  const [demoSource, setDemoSource] = useState<string | undefined>(undefined);
  const container = useRef<HTMLDivElement | null>(null);
  const plateCanvas = useRef<HTMLCanvasElement | null>(null);

  const layer = layerById(doc, selected);

  useEffect(() => {
    if (!jobId) return;
    fetch(`/api/jobs/${jobId}`)
      .then((response) => (response.ok ? response.json() : null))
      .then((meta) => {
        if (meta?.demo) setDemoSource(meta.demo_source || "recorded run");
      })
      .catch(() => undefined);
  }, [jobId]);

  const toPage = useCallback(
    (event: { clientX: number; clientY: number }) => {
      const rect = container.current?.getBoundingClientRect();
      if (!rect) return { x: 0, y: 0 };
      return { x: (event.clientX - rect.left - offset.x) / zoom, y: (event.clientY - rect.top - offset.y) / zoom };
    },
    [offset, zoom],
  );

  useEffect(() => {
    const element = container.current;
    if (!element) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      setZoom((value) => Math.min(3, Math.max(0.15, value * (event.deltaY > 0 ? 0.92 : 1.08))));
    };
    element.addEventListener("wheel", onWheel, { passive: false });
    return () => element.removeEventListener("wheel", onWheel);
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
        event.preventDefault();
        event.shiftKey ? editor.redo() : editor.undo();
      } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") {
        event.preventDefault();
        editor.redo();
      } else if (event.key === "Escape") {
        setSelected(null);
      } else if (event.key === "Delete" && selected) {
        editor.commit((draftDoc) => {
          const target = draftDoc.layers.find((item) => item.id === selected);
          if (target) target.action = "skip";
        }, [selected]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [editor, selected]);

  const sampleColor = useCallback(
    (x: number, y: number): number[] => {
      const canvas = plateCanvas.current;
      if (!canvas || !doc) return [246, 240, 226];
      const context = canvas.getContext("2d");
      if (!context) return [246, 240, 226];
      const data = context.getImageData(Math.max(0, Math.min(canvas.width - 5, Math.round(x))), Math.max(0, Math.min(canvas.height - 5, Math.round(y))), 5, 5).data;
      let r = 0, g = 0, b = 0, n = 0;
      for (let i = 0; i < data.length; i += 4) {
        r += data[i];
        g += data[i + 1];
        b += data[i + 2];
        n += 1;
      }
      return [Math.round(r / n), Math.round(g / n), Math.round(b / n)];
    },
    [doc],
  );

  useEffect(() => {
    if (!doc || !container.current) return;
    const rect = container.current.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const fit = Math.min((rect.width - 60) / doc.width, (rect.height - 90) / doc.height);
    setZoom(fit);
    setOffset({ x: (rect.width - doc.width * fit) / 2, y: (rect.height - doc.height * fit) / 2 });
    if (!selected) {
      const first = doc.layers.find((item) => item.kind === "text" && item.action !== "skip");
      if (first) setSelected(first.id);
    }
    // Fit once per document load; later zooms stay the user's.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc?.id]);

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!doc) return;
    const point = toPage(event);
    if (tool === "cover") {
      setDraft({ mode: "cover", startX: point.x, startY: point.y, currentX: point.x, currentY: point.y });
      return;
    }
    if (event.target === event.currentTarget || (event.target as HTMLElement).dataset.background === "true") {
      setDraft({ mode: "pan", startX: event.clientX, startY: event.clientY, originX: offset.x, originY: offset.y });
    }
  };

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!draft || !doc) return;
    const point = toPage(event);
    if (draft.mode === "pan") {
      setOffset({ x: draft.originX + (event.clientX - draft.startX), y: draft.originY + (event.clientY - draft.startY) });
    } else if (draft.mode === "move" || draft.mode === "resize") {
      const dx = point.x - (draft.mode === "move" ? draft.startX : draft.startX);
      const dy = point.y - (draft.mode === "move" ? draft.startY : draft.startY);
      const [x1, y1, x2, y2] = draft.box;
      const box: [number, number, number, number] =
        draft.mode === "move"
          ? [x1 + dx, y1 + dy, x2 + dx, y2 + dy]
          : [x1, y1, Math.max(x1 + 30, x2 + dx), Math.max(y1 + 20, y2 + dy)];
      editor.preview((draftDoc) => {
        const target = draftDoc.layers.find((item) => item.id === draft.layerId);
        if (target) target.box = box.map((value) => Math.round(value)) as [number, number, number, number];
      }, [draft.layerId]);
    } else if (draft.mode === "cover") {
      setDraft({ ...draft, currentX: point.x, currentY: point.y });
    }
  };

  const onPointerUp = async () => {
    if (!draft) return;
    if (draft.mode === "move" || draft.mode === "resize") {
      editor.finish(draft.snapshot);
      await editor.layout(draft.layerId);
    }
    if (draft.mode === "cover" && doc) {
      const box = [
        Math.round(Math.min(draft.startX, draft.currentX)),
        Math.round(Math.min(draft.startY, draft.currentY)),
        Math.round(Math.max(draft.startX, draft.currentX)),
        Math.round(Math.max(draft.startY, draft.currentY)),
      ];
      if (box[2] - box[0] > 8 && box[3] - box[1] > 8) {
        const fill = sampleColor(box[0] - 4, box[1] - 4);
        const response = await fetch(`/api/jobs/${jobId}/cover`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ box, fill }),
        });
        if (response.ok) {
          const next = (await response.json()) as Document;
          editor.commit((draftDoc) => {
            draftDoc.layers = next.layers;
          });
        }
      }
    }
    setDraft(null);
  };

  const updateLayer = (mutate: (target: Layer) => void) => {
    if (!selected) return;
    editor.commit((draftDoc) => {
      const target = draftDoc.layers.find((item) => item.id === selected);
      if (target) mutate(target);
    }, [selected]);
  };

  const textLayers = useMemo(
    () => (doc ? [...doc.layers].sort((a, b) => a.z - b.z) : []),
    [doc],
  );

  if (!doc) {
    return <div className="p-10 text-sm text-ink/60">Loading job {jobId}…</div>;
  }

  const coverDraft = draft?.mode === "cover" ? draft : null;

  return (
    <div className="flex h-screen flex-col bg-paper text-ink">
      {demoSource && <DemoBadge source={demoSource} />}
      <header className="flex flex-wrap items-center gap-3 border-b border-sand px-4 py-2 text-sm">
        <a href="/" className="font-semibold">
          Naqsh
        </a>
        <span className="text-ink/40">job {doc.id}</span>
        <button className="rounded border border-sand px-2 py-1" onClick={editor.undo} disabled={!editor.canUndo}>
          Undo
        </button>
        <button className="rounded border border-sand px-2 py-1" onClick={editor.redo} disabled={!editor.canRedo}>
          Redo
        </button>
        <button
          className={`rounded border px-2 py-1 ${tool === "cover" ? "border-lacquer bg-lacquer text-paper" : "border-sand"}`}
          onClick={() => setTool(tool === "cover" ? "select" : "cover")}
        >
          Cover patch
        </button>
        <label className="flex items-center gap-1">
          Numerals
          <select
            className="rounded border border-sand bg-white px-1 py-0.5"
            value={doc.numerals}
            onChange={(event) =>
              editor.commit((draftDoc) => {
                draftDoc.numerals = event.target.value as Document["numerals"];
              })
            }
          >
            <option value="latin">Latin</option>
            <option value="arabic-indic">Arabic-Indic</option>
          </select>
        </label>
        <label className="flex items-center gap-1">
          Register
          <select
            className="rounded border border-sand bg-white px-1 py-0.5"
            value={doc.register}
            onChange={(event) =>
              editor.commit((draftDoc) => {
                draftDoc.register = event.target.value as Document["register"];
              })
            }
          >
            <option value="egyptian">Egyptian</option>
            <option value="msa">MSA</option>
          </select>
        </label>
        <label className="flex items-center gap-1">
          <input type="checkbox" checked={showOriginal} onChange={(event) => setShowOriginal(event.target.checked)} />
          Original
        </label>
        <div className="ms-auto flex gap-2">
          <a className="rounded border border-sand px-2 py-1" href={`/api/jobs/${jobId}/export.svg`} target="_blank" rel="noreferrer">
            SVG
          </a>
          <a className="rounded border border-sand px-2 py-1" href={`/api/jobs/${jobId}/export-outlined.svg`} target="_blank" rel="noreferrer">
            SVG outlined
          </a>
          <a className="rounded border border-sand px-2 py-1" href={`/api/jobs/${jobId}/export.png`}>
            PNG
          </a>
          <a className="rounded bg-nile px-2 py-1 text-paper" href={`/api/jobs/${jobId}/export.zip`}>
            Bundle
          </a>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <div
          ref={container}
          className={`relative flex-1 overflow-hidden ${tool === "cover" ? "cursor-crosshair" : "cursor-grab"}`}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
        >
          <div style={{ transform: `translate(${offset.x}px, ${offset.y}px)` }}>
            <svg
              width={doc.width * zoom}
              height={doc.height * zoom}
              viewBox={`0 0 ${doc.width} ${doc.height}`}
              style={{ background: "white", boxShadow: "0 4px 24px rgba(0,0,0,0.12)" }}
            >
              <image data-background="true" href={`/api/jobs/${jobId}/files/composite.png`} width={doc.width} height={doc.height} />
              {(showOriginal || split < 100) && (
                <>
                  <clipPath id="split-clip">
                    <rect x="0" y="0" width={showOriginal ? doc.width : (doc.width * split) / 100} height={doc.height} />
                  </clipPath>
                  <image
                    data-background="true"
                    href={`/api/jobs/${jobId}/files/source.png`}
                    width={doc.width}
                    height={doc.height}
                    clipPath="url(#split-clip)"
                    opacity={showOriginal ? 0.9 : 1}
                  />
                </>
              )}
              {textLayers
                .filter((item) => item.kind === "cover" && item.visible && item.fill.length === 3)
                .map((item) => (
                  <rect
                    key={item.id}
                    x={item.box[0]}
                    y={item.box[1]}
                    width={item.box[2] - item.box[0]}
                    height={item.box[3] - item.box[1]}
                    fill={`rgb(${item.fill[0]},${item.fill[1]},${item.fill[2]})`}
                  />
                ))}
              {textLayers
                .filter((item) => item.kind === "text" && item.visible && item.action !== "skip")
                .map((item) => (
                  <g key={item.id} onClick={() => setSelected(item.id)} style={{ cursor: "pointer" }}>
                    {item.lines.map((line, index) => (
                      <text
                        key={`${item.id}-${index}`}
                        x={line.x}
                        y={line.baseline}
                        fontFamily={FONT_LABELS[item.font_family] ?? item.font_family}
                        fontSize={line.size}
                        fill={`rgb(${item.color[0]},${item.color[1]},${item.color[2]})`}
                        textAnchor="middle"
                        direction="rtl"
                        unicodeBidi="embed"
                      >
                        {line.text}
                      </text>
                    ))}
                  </g>
                ))}
              {layer && (
                <g onPointerDown={(event) => {
                  if (layer.locked) return;
                  event.stopPropagation();
                  const point = toPage(event);
                  setSelected(layer.id);
                  setDraft({ mode: "move", layerId: layer.id, startX: point.x, startY: point.y, box: layer.box, snapshot: editor.document as Document });
                }}>
                  <rect
                    x={layer.box[0]}
                    y={layer.box[1]}
                    width={layer.box[2] - layer.box[0]}
                    height={layer.box[3] - layer.box[1]}
                    fill="none"
                    stroke="#a6342c"
                    strokeDasharray="6 4"
                    pointerEvents="all"
                  />
                  <rect
                    x={layer.box[2] - 10}
                    y={layer.box[3] - 10}
                    width={20}
                    height={20}
                    fill="#a6342c"
                    style={{ cursor: "nwse-resize" }}
                    onPointerDown={(event) => {
                      event.stopPropagation();
                      const point = toPage(event);
                      setDraft({ mode: "resize", layerId: layer.id, startX: point.x, startY: point.y, box: layer.box, snapshot: editor.document as Document });
                    }}
                  />
                </g>
              )}
              {coverDraft && (
                <rect
                  x={Math.min(coverDraft.startX, coverDraft.currentX)}
                  y={Math.min(coverDraft.startY, coverDraft.currentY)}
                  width={Math.abs(coverDraft.currentX - coverDraft.startX)}
                  height={Math.abs(coverDraft.currentY - coverDraft.startY)}
                  fill="rgba(166,52,44,0.25)"
                  stroke="#a6342c"
                />
              )}
            </svg>
          </div>
          <div className="absolute bottom-4 start-4 flex items-center gap-2 rounded bg-white/80 px-2 py-1 text-xs">
            <span>{Math.round(zoom * 100)}%</span>
            <input type="range" min={30} max={100} value={split} onChange={(event) => setSplit(Number(event.target.value))} />
            <span>before/after</span>
          </div>
          <canvas ref={plateCanvas} className="hidden" />
          <img
            src={`/api/jobs/${jobId}/files/composite.png`}
            alt=""
            className="hidden"
            onLoad={(event) => {
              const image = event.currentTarget;
              const canvas = plateCanvas.current;
              if (canvas && image.naturalWidth) {
                canvas.width = image.naturalWidth;
                canvas.height = image.naturalHeight;
                canvas.getContext("2d")?.drawImage(image, 0, 0);
              }
            }}
          />
        </div>

        <aside className="flex w-80 shrink-0 flex-col overflow-y-auto border-s border-sand bg-white/70 p-3 text-sm">
          <h2 className="mb-2 text-xs uppercase tracking-widest text-ink/50">Region</h2>
          {!layer && <p className="text-ink/50">Select a region on the canvas or in the list.</p>}
          {layer && layer.kind === "text" && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs">{layer.id}</span>
                <span className="rounded bg-sand px-1 text-xs">{layer.type}</span>
              </div>
              <label className="block text-xs text-ink/50">Arabic</label>
              <textarea
                dir="rtl"
                lang="ar"
                className="h-20 w-full rounded border border-sand p-2 font-arabic text-lg"
                value={layer.arabic[doc.register] ?? ""}
                onChange={(event) => {
                  const value = event.target.value;
                  updateLayer((target) => {
                    target.arabic[doc.register] = value;
                  });
                }}
                onBlur={() => void editor.layout(layer.id)}
              />
              <div className="flex items-center gap-2">
                <button
                  className="rounded border border-sand px-2 py-1"
                  onClick={async () => {
                    const cost = await editor.retranslate(layer.id, doc.register);
                    setRetranslateCost(cost);
                  }}
                >
                  Re-translate
                </button>
                {retranslateCost !== null && <span className="text-xs text-ink/50">${retranslateCost.toFixed(4)}</span>}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <label className="text-xs">
                  Font
                  <select
                    className="mt-1 w-full rounded border border-sand bg-white px-1 py-1"
                    value={layer.font_family}
                    onChange={(event) => {
                      const value = event.target.value;
                      updateLayer((target) => {
                        target.font_family = value;
                      });
                      void editor.layout(layer.id);
                    }}
                  >
                    {FONTS.map((font) => (
                      <option key={font} value={font}>
                        {FONT_LABELS[font]}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="text-xs">
                  Size
                  <input
                    type="number"
                    className="mt-1 w-full rounded border border-sand px-1 py-1"
                    value={layer.font_size}
                    onChange={(event) => {
                      const value = Number(event.target.value);
                      updateLayer((target) => {
                        target.font_size = value;
                      });
                    }}
                    onBlur={() => void editor.layout(layer.id)}
                  />
                </label>
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs">Colour</label>
                <input
                  type="color"
                  value={`#${layer.color.map((value) => value.toString(16).padStart(2, "0")).join("")}`}
                  onChange={(event) => {
                    const value = event.target.value;
                    updateLayer((target) => {
                      target.color = [parseInt(value.slice(1, 3), 16), parseInt(value.slice(3, 5), 16), parseInt(value.slice(5, 7), 16)];
                    });
                  }}
                />
                <button
                  className={`ms-auto rounded border px-2 py-1 text-xs ${layer.action === "skip" ? "border-lacquer text-lacquer" : "border-sand"}`}
                  onClick={() =>
                    updateLayer((target) => {
                      target.action = target.action === "skip" ? "translate" : "skip";
                    })
                  }
                >
                  {layer.action === "skip" ? "Skipped" : "Translate"}
                </button>
              </div>
              <button
                className="rounded border border-sand px-2 py-1 text-xs"
                onClick={() => void editor.reload()}
              >
                Reset region (reload document)
              </button>
            </div>
          )}
          {layer && layer.kind === "cover" && (
            <div className="space-y-2 text-xs">
              <p>Cover patch {layer.id}</p>
              <p className="text-ink/50">Fill {layer.fill.join(", ")}</p>
            </div>
          )}

          <h2 className="mb-2 mt-4 text-xs uppercase tracking-widest text-ink/50">Layers</h2>
          <ul className="space-y-1 text-xs">
            {textLayers.map((item) => (
              <li
                key={item.id}
                className={`flex items-center gap-2 rounded border px-2 py-1 ${selected === item.id ? "border-lacquer" : "border-sand/60"}`}
              >
                <button
                  title="visible"
                  onClick={() => updateLayerFor(item.id, (target) => (target.visible = !target.visible))}
                >
                  {item.visible ? "👁" : "–"}
                </button>
                <button title="lock" onClick={() => updateLayerFor(item.id, (target) => (target.locked = !target.locked))}>
                  {item.locked ? "🔒" : "🔓"}
                </button>
                <button className="flex-1 text-start" onClick={() => setSelected(item.id)}>
                  {item.id} · {item.kind === "cover" ? "cover" : item.type}
                </button>
                <button onClick={() => nudgeZ(item.id, 1)}>↑</button>
                <button onClick={() => nudgeZ(item.id, -1)}>↓</button>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </div>
  );

  function updateLayerFor(id: string, mutate: (target: Layer) => void) {
    editor.commit((draftDoc) => {
      const target = draftDoc.layers.find((item) => item.id === id);
      if (target) mutate(target);
    }, [id]);
  }

  function nudgeZ(id: string, delta: number) {
    editor.commit((draftDoc) => {
      const target = draftDoc.layers.find((item) => item.id === id);
      if (target) target.z = target.z + delta;
    }, [id]);
  }
}
