import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Circle, Eye, EyeOff, Lock, Maximize2, Minus, MousePointer2, Pencil, Pipette, Plus, Redo2, Square, Type, Undo2, Unlock } from "lucide-react";
import ColorField from "./ColorField";
import StateIllustration from "../StateIllustration";
import DemoBadge from "../DemoBadge";
import { layerById, FONTS, FONT_LABELS, FONT_SAMPLES, type Document, type Layer } from "./types";
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
  const [tool, setTool] = useState<"select" | "cover" | "eyedropper">("select");
  const [coverShape, setCoverShape] = useState<"rect" | "ellipse">("rect");
  const [coverFill, setCoverFill] = useState<number[]>([230, 226, 216]);
  const [exportOpen, setExportOpen] = useState(false);
  const [exporting, setExporting] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [sampleFrom, setSampleFrom] = useState<"plate" | "original">("plate");
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [dragLayer, setDragLayer] = useState<string | null>(null);
  const [showOriginal, setShowOriginal] = useState(false);
  const [split, setSplit] = useState(100);
  const [draft, setDraft] = useState<DragState>(null);
  const [retranslateCost, setRetranslateCost] = useState<number | null>(null);
  const [retranslateBusy, setRetranslateBusy] = useState(false);
  const [retranslateError, setRetranslateError] = useState<string | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const sizeTimer = useRef<number | null>(null);
  const [demoSource, setDemoSource] = useState<string | undefined>(undefined);
  const container = useRef<HTMLDivElement | null>(null);
  const plateCanvas = useRef<HTMLCanvasElement | null>(null);
  const sourceCanvas = useRef<HTMLCanvasElement | null>(null);
  const splitDrag = useRef(false);

  const layer = layerById(doc, selected);
  const sceneLayer = doc?.layers.find((item) => item.kind === "scene") ?? null;
  const bubbleLayers = doc?.layers.filter((item) => item.kind === "bubble") ?? [];

  const fitView = useCallback(() => {
    if (!doc || !container.current) return;
    const rect = container.current.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const fit = Math.min((rect.width - 60) / doc.width, (rect.height - 90) / doc.height);
    setZoom(fit);
    setOffset({ x: (rect.width - doc.width * fit) / 2, y: (rect.height - doc.height * fit) / 2 });
  }, [doc]);

  const zoomBy = useCallback((factor: number) => {
    setZoom((value) => Math.min(3, Math.max(0.1, value * factor)));
  }, []);

  // Fit the page once it loads and select the first editable region, so the panel is
  // never empty on open or after a reload.
  useEffect(() => {
    if (!doc) return;
    fitView();
    if (!selected) {
      const first = doc.layers.find((item) => item.kind === "text" && item.action !== "skip");
      if (first) setSelected(first.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc?.id]);



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
      } else if ((event.key === "+" || event.key === "=") && !(event.target as HTMLElement)?.closest("input, textarea, select")) {
        event.preventDefault();
        zoomBy(1.1);
      } else if (event.key === "-" && !(event.target as HTMLElement)?.closest("input, textarea, select")) {
        event.preventDefault();
        zoomBy(0.9);
      } else if (event.key === "0" && !(event.target as HTMLElement)?.closest("input, textarea, select")) {
        event.preventDefault();
        fitView();
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
  }, [editor, selected, fitView, zoomBy]);

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!doc) return;
    const point = toPage(event);
    if (tool === "eyedropper") {
      const canvas = sampleFrom === "original" ? sourceCanvas.current : plateCanvas.current;
      const context = canvas?.getContext("2d");
      if (canvas && context) {
        const x = Math.max(0, Math.min(canvas.width - 1, Math.round(point.x)));
        const y = Math.max(0, Math.min(canvas.height - 1, Math.round(point.y)));
        const pixel = context.getImageData(x, y, 1, 1).data;
        const rgb: [number, number, number] = [pixel[0], pixel[1], pixel[2]];
        if (layer && layer.kind === "text") {
          updateLayer((target) => {
            target.color = rgb;
          });
        } else if (layer && layer.kind === "cover") {
          updateLayer((target) => {
            target.fill = rgb;
          });
        } else {
          setCoverFill(rgb);
        }
        setToast("Colour picked from the page");
        window.setTimeout(() => setToast(null), 1800);
      }
      return;
    }
    if (tool === "cover") {
      setDraft({ mode: "cover", startX: point.x, startY: point.y, currentX: point.x, currentY: point.y });
      return;
    }
    if (event.target === event.currentTarget || (event.target as HTMLElement).dataset.background === "true") {
      setDraft({ mode: "pan", startX: event.clientX, startY: event.clientY, originX: offset.x, originY: offset.y });
    }
  };

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>) => {
    if (splitDrag.current && doc) {
      const point = toPage(event);
      setSplit(Math.min(100, Math.max(0, Math.round((point.x / doc.width) * 100))));
      return;
    }
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
    if (splitDrag.current) {
      splitDrag.current = false;
      return;
    }
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
        const fill = coverFill;
        const response = await fetch(`/api/jobs/${jobId}/cover`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ box, fill, shape: coverShape }),
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

  const runExport = async (name: string, href: string) => {
    setExportOpen(false);
    setExporting(name);
    try {
      const response = await fetch(href);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      const extension = blob.type.includes("svg") ? "svg" : blob.type.includes("zip") ? "zip" : "png";
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `naqsh-${jobId}-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.${extension}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setToast(`${name} exported · ${(blob.size / 1024).toFixed(0)} KB`);
    } catch {
      setToast(`${name} failed — try again`);
    } finally {
      setExporting(null);
      window.setTimeout(() => setToast(null), 3200);
    }
  };

  const textLayers = useMemo(
    () => (doc ? [...doc.layers].sort((a, b) => a.z - b.z) : []),
    [doc],
  );

  if (!doc) {
    return (
      <div className="p-10">
        <StateIllustration kind="loading" title="Loading the job" detail={jobId} />
      </div>
    );
  }

  const coverDraft = draft?.mode === "cover" ? draft : null;

  return (
    <div className="flex h-screen flex-col bg-paper text-ink">
      {demoSource && <DemoBadge source={demoSource} />}
      <header className="flex h-12 flex-wrap items-center gap-3 border-b border-border bg-panel px-4 text-sm">
        <a href="/" className="font-semibold">
          Naqsh
        </a>
        <span className="text-ink/70">job {doc.id}</span>
        <button
          aria-label="Undo"
          title="Undo (Ctrl+Z)"
          className="flex h-8 w-8 items-center justify-center"
          onClick={editor.undo}
          disabled={!editor.canUndo}
        >
          <Undo2 size={16} />
        </button>
        <button
          aria-label="Redo"
          title="Redo (Ctrl+Shift+Z)"
          className="flex h-8 w-8 items-center justify-center"
          onClick={editor.redo}
          disabled={!editor.canRedo}
        >
          <Redo2 size={16} />
        </button>
        <label className="flex items-center gap-1" title="How numbers are drawn in price layers only. The sample next to the select is live.">
          Digits
          <select
            data-testid="numerals-select"
            className="rounded border border-sand bg-panel px-1 py-0.5"
            value={doc.numerals}
            onChange={(event) => {
              editor.commit((draftDoc) => {
                draftDoc.numerals = event.target.value as Document["numerals"];
              });
              window.setTimeout(() => void editor.reload(), 250);
            }}
          >
            <option value="latin">0123</option>
            <option value="arabic-indic">٠١٢٣</option>
          </select>
        </label>
        <button
          aria-label="Original"
          aria-pressed={showOriginal}
          title="Show the original page and hide every overlay (O)"
          className="flex h-8 items-center gap-1.5 px-2"
          onClick={() => setShowOriginal((value) => !value)}
        >
          {showOriginal ? <EyeOff size={16} /> : <Eye size={16} />}
          <span>Original</span>
        </button>

        <div className="flex items-center gap-1" role="group" aria-label="Zoom">
          <button
            aria-label="Zoom out"
            title="Zoom out (-)"
            className="flex h-8 w-8 items-center justify-center"
            onClick={() => zoomBy(0.9)}
          >
            <Minus size={16} />
          </button>
          <span data-testid="zoom-level" className="w-12 text-center text-xs text-ink/70">
            {Math.round(zoom * 100)}%
          </span>
          <button
            aria-label="Zoom in"
            title="Zoom in (+)"
            className="flex h-8 w-8 items-center justify-center"
            onClick={() => zoomBy(1.1)}
          >
            <Plus size={16} />
          </button>
          <button
            aria-label="Fit to screen"
            title="Fit to screen (0)"
            className="flex h-8 w-8 items-center justify-center"
            onClick={fitView}
          >
            <Maximize2 size={16} />
          </button>
        </div>
        <div className="relative ms-auto">
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={exportOpen}
            className="h-8 rounded bg-accent-strong px-3 text-white"
            onClick={() => setExportOpen((value) => !value)}
          >
            Export
          </button>
          {exportOpen && (
            <div role="menu" className="absolute end-0 top-10 z-30 w-72 rounded border border-border bg-panel p-1 shadow-xl">
              {[
                ["Layered SVG", "Editable text layers, opens in Figma/Inkscape", `/api/jobs/${jobId}/export.svg`],
                ["Outlined SVG", "Text as paths; looks right without fonts", `/api/jobs/${jobId}/export-outlined.svg`],
                ["PNG", "Flat image at source size", `/api/jobs/${jobId}/export.png`],
                ["Bundle (ZIP)", "SVGs, plate, fonts and licences", `/api/jobs/${jobId}/export.zip`],
              ].map(([name, description, href]) => (
                <button
                  key={name}
                  role="menuitem"
                  className="block w-full rounded px-2 py-2 text-start"
                  onClick={() => void runExport(name, href)}
                >
                  <span className="block text-sm">{name}</span>
                  <span className="block text-[11px] leading-tight text-ink/70">{description}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <nav aria-label="Tools" className="flex w-12 shrink-0 flex-col items-center gap-1 border-e border-border bg-panel py-2">
          <button
            aria-label="Select and move"
            title="Select / move (V)"
            aria-pressed={tool === "select"}
            className="flex h-9 w-9 items-center justify-center"
            onClick={() => setTool("select")}
          >
            <MousePointer2 size={17} />
          </button>
          <button
            aria-label="Text"
            title="Text: click a text region to edit it (T)"
            className="flex h-9 w-9 items-center justify-center"
            onClick={() => {
              setTool("select");
              setToast("Text tool: click a text region to edit it");
              window.setTimeout(() => setToast(null), 2000);
            }}
          >
            <Type size={17} />
          </button>
          <button
            aria-label="Cover patch"
            title="Cover patch (C): drag to cover an area"
            aria-pressed={tool === "cover"}
            className="flex h-9 w-9 items-center justify-center"
            onClick={() => setTool("cover")}
          >
            <Square size={17} />
          </button>
          <button
            aria-label="Eyedropper"
            title="Eyedropper (I): pick a colour from the page"
            aria-pressed={tool === "eyedropper"}
            className="flex h-9 w-9 items-center justify-center"
            onClick={() => setTool("eyedropper")}
          >
            <Pipette size={17} />
          </button>
          {tool === "eyedropper" && (
            <div className="mt-1 flex flex-col gap-1 border-t border-border pt-1">
              <button
                aria-label="Sample clean plate"
                title="Sample from the clean plate"
                aria-pressed={sampleFrom === "plate"}
                className="h-7 w-9 text-[10px]"
                onClick={() => setSampleFrom("plate")}
              >
                Plate
              </button>
              <button
                aria-label="Sample original"
                title="Sample from the original page"
                aria-pressed={sampleFrom === "original"}
                className="h-7 w-9 text-[10px]"
                onClick={() => setSampleFrom("original")}
              >
                Orig
              </button>
            </div>
          )}
          {tool === "cover" && (
            <div className="mt-1 flex flex-col gap-1 border-t border-border pt-1">
              <button
                aria-label="Rectangle patch"
                title="Rectangle patch"
                aria-pressed={coverShape === "rect"}
                className="flex h-8 w-9 items-center justify-center"
                onClick={() => setCoverShape("rect")}
              >
                <Square size={15} />
              </button>
              <button
                aria-label="Ellipse patch"
                title="Ellipse patch"
                aria-pressed={coverShape === "ellipse"}
                className="flex h-8 w-9 items-center justify-center"
                onClick={() => setCoverShape("ellipse")}
              >
                <Circle size={15} />
              </button>
            </div>
          )}
        </nav>
        <div
          ref={container}
          className={`relative flex-1 overflow-hidden bg-[#0b0c0f] ${tool === "cover" ? "cursor-crosshair" : "cursor-grab"}`}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
        >
          <div style={{ transform: `translate(${offset.x}px, ${offset.y}px)` }}>
            <svg
              data-testid="canvas-svg"
              width={doc.width * zoom}
              height={doc.height * zoom}
              viewBox={`0 0 ${doc.width} ${doc.height}`}
              style={{ background: "white", boxShadow: "0 4px 24px rgba(0,0,0,0.12)" }}
            >
              {sceneLayer && sceneLayer.visible ? (
                <image
                  data-background="true"
                  href={`/api/jobs/${jobId}/files/${sceneLayer.asset}`}
                  width={doc.width}
                  height={doc.height}
                />
              ) : (
                <image data-background="true" href={`/api/jobs/${jobId}/files/composite.png`} width={doc.width} height={doc.height} />
              )}
              {!showOriginal &&
                bubbleLayers
                  .filter((item) => item.visible && item.asset)
                  .map((item) => (
                    <image
                      key={item.id}
                      href={`/api/jobs/${jobId}/files/${item.asset}`}
                      x={item.box[0]}
                      y={item.box[1]}
                      width={item.box[2] - item.box[0]}
                      height={item.box[3] - item.box[1]}
                    />
                  ))}
              {!showOriginal &&
                textLayers
                  .filter((item) => item.kind === "cover" && item.visible && item.fill.length === 3)
                  .map((item) =>
                    item.shape === "ellipse" ? (
                      <ellipse
                        key={item.id}
                        cx={(item.box[0] + item.box[2]) / 2}
                        cy={(item.box[1] + item.box[3]) / 2}
                        rx={(item.box[2] - item.box[0]) / 2}
                        ry={(item.box[3] - item.box[1]) / 2}
                        fill={`rgb(${item.fill[0]},${item.fill[1]},${item.fill[2]})`}
                      />
                    ) : (
                      <rect
                        key={item.id}
                        x={item.box[0]}
                        y={item.box[1]}
                        width={item.box[2] - item.box[0]}
                        height={item.box[3] - item.box[1]}
                        fill={`rgb(${item.fill[0]},${item.fill[1]},${item.fill[2]})`}
                      />
                    ),
                  )}
              {!showOriginal &&
                textLayers
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
              {!showOriginal && layer && (
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
                    stroke="#5B6CFF"
                    strokeDasharray="6 4"
                    pointerEvents="all"
                  />
                  <rect
                    x={layer.box[2] - 10}
                    y={layer.box[3] - 10}
                    width={20}
                    height={20}
                    fill="#5B6CFF"
                    style={{ cursor: "nwse-resize" }}
                    onPointerDown={(event) => {
                      event.stopPropagation();
                      const point = toPage(event);
                      setDraft({ mode: "resize", layerId: layer.id, startX: point.x, startY: point.y, box: layer.box, snapshot: editor.document as Document });
                    }}
                  />
                </g>
              )}
              {coverDraft && coverShape === "ellipse" ? (
                <ellipse
                  cx={(coverDraft.startX + coverDraft.currentX) / 2}
                  cy={(coverDraft.startY + coverDraft.currentY) / 2}
                  rx={Math.abs(coverDraft.currentX - coverDraft.startX) / 2}
                  ry={Math.abs(coverDraft.currentY - coverDraft.startY) / 2}
                  fill="rgba(91,108,255,0.22)"
                  stroke="#5B6CFF"
                />
              ) : coverDraft ? (
                <rect
                  x={Math.min(coverDraft.startX, coverDraft.currentX)}
                  y={Math.min(coverDraft.startY, coverDraft.currentY)}
                  width={Math.abs(coverDraft.currentX - coverDraft.startX)}
                  height={Math.abs(coverDraft.currentY - coverDraft.startY)}
                  fill="rgba(91,108,255,0.22)"
                  stroke="#5B6CFF"
                />
              ) : null}
              {showOriginal ? (
                <image
                  data-background="true"
                  href={`/api/jobs/${jobId}/files/source.png`}
                  width={doc.width}
                  height={doc.height}
                />
              ) : (
                split < 100 && (
                  <>
                    <clipPath id="split-clip">
                      <rect x="0" y="0" width={(doc.width * split) / 100} height={doc.height} />
                    </clipPath>
                    <image
                      data-background="true"
                      href={`/api/jobs/${jobId}/files/source.png`}
                      width={doc.width}
                      height={doc.height}
                      clipPath="url(#split-clip)"
                    />
                    <line
                      x1={(doc.width * split) / 100}
                      y1={0}
                      x2={(doc.width * split) / 100}
                      y2={doc.height}
                      stroke="#5B6CFF"
                      strokeWidth={2}
                      pointerEvents="all"
                      style={{ cursor: "ew-resize" }}
                      onPointerDown={(event) => {
                        event.stopPropagation();
                        splitDrag.current = true;
                      }}
                    />
                  </>
                )
              )}
            </svg>
          </div>
          <div
            dir="ltr"
            data-testid="before-after-control"
            className="absolute bottom-4 left-1/2 flex -translate-x-1/2 items-center gap-3 rounded border border-border bg-panel/95 px-3 py-1.5 text-xs text-ink"
          >
            <span className="text-ink/70">Before / after</span>
            <input
              aria-label="Before and after reveal"
              type="range"
              min={0}
              max={100}
              value={showOriginal ? 100 : split}
              disabled={showOriginal}
              onChange={(event) => setSplit(Number(event.target.value))}
              className="w-48"
            />
            <span className="w-9 text-end text-ink/70">{showOriginal ? 100 : split}%</span>
          </div>
          <canvas ref={plateCanvas} className="hidden" />
          <canvas ref={sourceCanvas} className="hidden" />
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
          <img
            src={`/api/jobs/${jobId}/files/source.png`}
            alt=""
            className="hidden"
            onLoad={(event) => {
              const image = event.currentTarget;
              const canvas = sourceCanvas.current;
              if (canvas && image.naturalWidth) {
                canvas.width = image.naturalWidth;
                canvas.height = image.naturalHeight;
                canvas.getContext("2d")?.drawImage(image, 0, 0);
              }
            }}
          />
        </div>

        <aside className="flex w-80 shrink-0 flex-col gap-1 overflow-y-auto border-s border-border bg-panel p-4 text-sm">
          <h2 className="mb-2 text-xs tracking-wide text-ink/70">Region</h2>
          {!layer && <StateIllustration compact kind="empty" title="No region selected" detail="Pick a region on the canvas or in the list." />}
          {layer && layer.kind === "text" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs">{layer.id}</span>
                <span className="rounded bg-raised px-1 text-xs">{layer.type}</span>
              </div>
              <label className="block text-xs text-ink/70">Arabic</label>
              <textarea
                dir="rtl"
                lang="ar"
                aria-label="Arabic text"
                className="h-20 w-full rounded border border-sand p-2 font-arabic text-lg"
                value={layer.arabic[doc.register] ?? ""}
                onChange={(event) => {
                  const value = event.target.value;
                  updateLayer((target) => {
                    target.arabic[doc.register] = value;
                  });
                }}
                onBlur={(event) => void editor.layout(layer.id, { text: event.target.value })}
              />

              <div className="flex flex-wrap items-center gap-2">
                <button
                  className="rounded border border-sand px-2 py-1 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={retranslateBusy}
                  title="Ask Spark for a new Arabic line for this region. Costs about $0.001 and is blocked while one call is in flight."
                  onClick={async () => {
                    setRetranslateBusy(true);
                    setRetranslateError(null);
                    try {
                      const cost = await editor.retranslate(layer.id, doc.register);
                      setRetranslateCost(cost);
                    } catch (error) {
                      setRetranslateError(error instanceof Error ? error.message : "Re-translate failed");
                    } finally {
                      setRetranslateBusy(false);
                    }
                  }}
                >
                  {retranslateBusy ? "Translating…" : "Re-translate"}
                </button>
                {retranslateCost !== null && !retranslateBusy && (
                  <span className="text-xs text-ink/70">${retranslateCost.toFixed(4)}</span>
                )}
                <button
                  className="ms-auto rounded border border-sand px-2 py-1 text-xs disabled:opacity-50"
                  disabled={retranslateBusy}
                  title="Restore this region to its first AI result (text, font, size, colour, position). Undoable."
                  onClick={async () => {
                    setResetError(null);
                    try {
                      await editor.reset(layer.id);
                    } catch (error) {
                      setResetError(error instanceof Error ? error.message : "Reset failed");
                    }
                  }}
                >
                  Reset to AI result
                </button>
              </div>
              {retranslateError && <p className="text-xs text-lacquer">{retranslateError}</p>}
              {resetError && <p className="text-xs text-lacquer">{resetError}</p>}

              <div className="grid grid-cols-2 gap-2">
                <label className="text-xs">
                  Font
                  <select
                    data-testid="font-select"
                    className="mt-1 w-full rounded border border-sand bg-panel px-1 py-1"
                    value={layer.font_family}
                    onChange={(event) => {
                      const value = event.target.value;
                      updateLayer((target) => {
                        target.font_family = value;
                      });
                      void editor.layout(layer.id, { font_family: value });
                    }}
                  >
                    {FONTS.map((font) => (
                      <option key={font} value={font} style={{ fontFamily: FONT_LABELS[font] }}>
                        {`${FONT_LABELS[font]} — \u2067${FONT_SAMPLES[font]}\u2069`}
                      </option>
                    ))}
                  </select>
                  <span dir="rtl" lang="ar" className="mt-1 block font-arabic text-lg text-ink/70">
                    {FONT_SAMPLES[layer.font_family] ?? "أبجد هوز"}
                  </span>
                </label>
                <label className="text-xs">
                  Arabic style
                  <select
                    className="mt-1 w-full rounded border border-sand bg-panel px-1 py-1"
                    value={doc.register}
                    title="Switching shows that register's saved text. It does not re-translate; use Re-translate for that (about $0.001 per region)."
                    onChange={(event) => {
                      editor.commit((draftDoc) => {
                        draftDoc.register = event.target.value as Document["register"];
                      });
                      window.setTimeout(() => void editor.reload(), 250);
                    }}
                  >
                    <option value="egyptian">Egyptian colloquial</option>
                    <option value="msa">Modern Standard Arabic</option>
                  </select>
                  <span className="mt-1 block text-[10px] leading-tight text-ink/70">
                    Switching only shows that register. Re-translate writes it (about $0.001).
                  </span>
                </label>
              </div>

              <div className="text-xs">
                <div className="flex items-center gap-2">
                  <label htmlFor="size-number">Size</label>
                  <input
                    id="size-number"
                    data-testid="size-number"
                    type="number"
                    min={1}
                    max={1000}
                    className="w-16 rounded border border-sand px-1 py-1"
                    value={layer.font_size}
                    onChange={(event) => {
                      const value = Math.min(1000, Math.max(1, Number(event.target.value) || 1));
                      updateLayer((target) => {
                        target.font_size = value;
                      });
                      if (sizeTimer.current) window.clearTimeout(sizeTimer.current);
                      sizeTimer.current = window.setTimeout(() => void editor.layout(layer.id, { font_size: value }), 180);
                    }}
                    onBlur={() => void editor.layout(layer.id)}
                  />
                  <button
                    className="rounded border border-sand px-2 py-1 text-[11px]"
                    title="Fit the text to this region's box at the largest size that fits."
                    onClick={() => void editor.layout(layer.id, { font_size: 0 })}
                  >
                    Fit to box
                  </button>
                </div>
                <p className="mt-1 text-[10px] leading-tight text-ink/70">
                  Size is capped so the text stays inside the box; Fit to box sets the largest size that fits.
                </p>
                <input
                  data-testid="size-slider"
                  aria-label="Font size"
                  type="range"
                  min={1}
                  max={1000}
                  value={Math.min(1000, Math.max(1, layer.font_size))}
                  className="mt-2 w-full"
                  onChange={(event) => {
                    const value = Number(event.target.value);
                    updateLayer((target) => {
                      target.font_size = value;
                    });
                    if (sizeTimer.current) window.clearTimeout(sizeTimer.current);
                    sizeTimer.current = window.setTimeout(() => void editor.layout(layer.id, { font_size: value }), 120);
                  }}
                />
              </div>

              <div className="flex items-center gap-2">
                <ColorField
                  value={layer.color}
                  onChange={(rgb) =>
                    updateLayer((target) => {
                      target.color = [rgb[0], rgb[1], rgb[2]];
                    })
                  }
                  onEyedropper={() => setTool("eyedropper")}
                />
                <label className="ms-auto flex items-center gap-2 text-xs">
                  <input
                    type="checkbox"
                    checked={layer.action !== "skip"}
                    onChange={(event) =>
                      updateLayer((target) => {
                        target.action = event.target.checked ? "translate" : "skip";
                      })
                    }
                  />
                  Localize region
                </label>
              </div>
              <p className="text-[10px] leading-tight text-ink/70">
                Localize off keeps the original artwork for this region (useful for logos and SFX).
              </p>
            </div>
          )}
          {layer && (layer.kind === "scene" || layer.kind === "bubble") && (
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs">{layer.id}</span>
                <span className="rounded bg-raised px-1 text-[10px]">{layer.kind}</span>
              </div>
              <label className="block">
                Name
                <input
                  className="mt-1 w-full px-1 py-1"
                  value={layer.name ?? ""}
                  onChange={(event) => {
                    const value = event.target.value;
                    updateLayerFor(layer.id, (target) => {
                      target.name = value.slice(0, 80);
                    });
                  }}
                />
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={layer.visible}
                  onChange={() => updateLayerFor(layer.id, (target) => (target.visible = !target.visible))}
                />
                Visible
              </label>
              <p className="text-[10px] leading-tight text-ink/70">
                {layer.kind === "scene"
                  ? "Scenery: the cleaned page with the bubbles cut out. Hide it to reveal nothing behind."
                  : "Speech bubble cut from the cleaned page. Hide it to see the scenery hole underneath."}
              </p>
            </div>
          )}
          {layer && layer.kind === "cover" && (
            <div className="space-y-3 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs">{layer.id}</span>
                <span className="rounded bg-raised px-1 text-xs">{layer.shape}</span>
              </div>
              <ColorField
                label="Fill"
                value={layer.fill.length === 3 ? layer.fill : [230, 226, 216]}
                onChange={(rgb) =>
                  updateLayer((target) => {
                    target.fill = rgb;
                  })
                }
                onEyedropper={() => setTool("eyedropper")}
              />
              <label className="block">
                Shape
                <select
                  className="mt-1 w-full px-1 py-1"
                  value={layer.shape}
                  onChange={(event) =>
                    updateLayer((target) => {
                      target.shape = event.target.value === "ellipse" ? "ellipse" : "rect";
                    })
                  }
                >
                  <option value="rect">Rectangle</option>
                  <option value="ellipse">Ellipse</option>
                </select>
              </label>
              <p className="text-[10px] leading-tight text-ink/70">
                Drag to move, use the corner handle to resize. The eyedropper picks a colour from the page.
              </p>
            </div>
          )}

          <h2 className="mb-2 mt-4 text-xs tracking-wide text-ink/70">Layers</h2>
          <ul className="space-y-1 text-xs" data-testid="layers-list">
            <li className="flex items-center gap-2 rounded border border-border bg-panel px-2 py-1 text-ink/70">
              <EyeOff size={13} />
              <Lock size={13} />
              <span className="flex-1">Original</span>
              <span className="text-[10px]">reference</span>
            </li>
            <li className="flex items-center gap-2 rounded border border-border bg-panel px-2 py-1 text-ink/70">
              <Eye size={13} />
              <Lock size={13} />
              <span className="flex-1">Clean plate</span>
              <span className="text-[10px]">background</span>
            </li>
            {[...textLayers].sort((a, b) => b.z - a.z).map((item) => (
              <li
                key={item.id}
                draggable
                onDragStart={() => setDragLayer(item.id)}
                onDragOver={(event) => event.preventDefault()}
                onDrop={() => {
                  if (dragLayer && dragLayer !== item.id) swapZ(dragLayer, item.id);
                  setDragLayer(null);
                }}
                className={`flex items-center gap-1.5 rounded border px-2 py-1 ${selected === item.id ? "border-accent" : "border-border"}`}
              >
                <button
                  aria-label={`Toggle ${item.id} visibility`}
                  title="Show/hide"
                  onClick={() => updateLayerFor(item.id, (target) => (target.visible = !target.visible))}
                >
                  {item.visible ? <Eye size={13} /> : <EyeOff size={13} />}
                </button>
                <button
                  aria-label={`Toggle ${item.id} lock`}
                  title="Lock"
                  onClick={() => updateLayerFor(item.id, (target) => (target.locked = !target.locked))}
                >
                  {item.locked ? <Lock size={13} /> : <Unlock size={13} />}
                </button>
                {renaming === item.id ? (
                  <input
                    autoFocus
                    className="min-w-0 flex-1 px-1 py-0.5 text-xs"
                    value={renameValue}
                    onChange={(event) => setRenameValue(event.target.value)}
                    onBlur={() => {
                      updateLayerFor(item.id, (target) => {
                        target.name = renameValue.slice(0, 80);
                      });
                      setRenaming(null);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") (event.target as HTMLInputElement).blur();
                      if (event.key === "Escape") setRenaming(null);
                    }}
                  />
                ) : (
                  <button
                    data-testid={`layer-name-${item.id}`}
                    className="min-w-0 flex-1 truncate text-start"
                    title="Click to select, double-click to rename, drag to reorder"
                    onClick={() => setSelected(item.id)}
                    onDoubleClick={() => {
                      setRenaming(item.id);
                      setRenameValue(item.name || item.id);
                    }}
                  >
                    {item.name || item.id}
                    <span className="ms-1 text-[10px] text-ink/70">
                      {item.kind === "cover" ? item.shape : item.type}
                    </span>
                  </button>
                )}
                <button
                  aria-label={`Rename ${item.id}`}
                  title="Rename layer"
                  onClick={() => {
                    setRenaming(item.id);
                    setRenameValue(item.name || item.id);
                  }}
                >
                  <Pencil size={12} />
                </button>
                <button aria-label="Move layer up" title="Move up (towards front)" onClick={() => nudgeZ(item.id, 1)}>
                  ↑
                </button>
                <button aria-label="Move layer down" title="Move down" onClick={() => nudgeZ(item.id, -1)}>
                  ↓
                </button>
              </li>
            ))}
          </ul>
        </aside>
      </div>
      {exporting && (
        <>
          <div className="fixed bottom-0 left-0 z-40 h-0.5 w-full bg-raised">
            <div className="export-progress h-full bg-accent" />
          </div>
          <div
            role="status"
            className="fixed bottom-6 end-6 z-40 rounded border border-border bg-panel px-4 py-2 text-sm text-fg shadow-xl"
          >
            Generating {exporting}…
          </div>
        </>
      )}
      {toast && !exporting && (
        <div
          role="status"
          className="fixed bottom-6 end-6 z-40 rounded border border-border bg-panel px-4 py-2 text-sm text-fg shadow-xl"
        >
          {toast}
        </div>
      )}
    </div>
  );

  function updateLayerFor(id: string, mutate: (target: Layer) => void) {
    editor.commit((draftDoc) => {
      const target = draftDoc.layers.find((item) => item.id === id);
      if (target) mutate(target);
    }, [id]);
  }

  function swapZ(a: string, b: string) {
    editor.commit((draftDoc) => {
      const first = draftDoc.layers.find((item) => item.id === a);
      const second = draftDoc.layers.find((item) => item.id === b);
      if (first && second) {
        const z = first.z;
        first.z = second.z;
        second.z = z;
      }
    }, [a, b]);
  }

  function nudgeZ(id: string, delta: number) {
    editor.commit((draftDoc) => {
      const target = draftDoc.layers.find((item) => item.id === id);
      if (target) target.z = target.z + delta;
    }, [id]);
  }
}
