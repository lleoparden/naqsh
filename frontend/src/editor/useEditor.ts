import { useCallback, useEffect, useMemo, useReducer, useRef } from "react";
import { cloneDocument, type Document, type History, type Layer } from "./types";

type Action =
  | { type: "load"; document: Document }
  | { type: "commit"; document: Document }
  | { type: "undo" }
  | { type: "redo" };

const initial: History = { past: [], present: null, future: [] };

function reducer(state: History, action: Action): History {
  switch (action.type) {
    case "load":
      return { past: [], present: action.document, future: [] };
    case "commit":
      if (!state.present) return { ...state, present: action.document };
      return { past: [...state.past.slice(-40), state.present], present: action.document, future: [] };
    case "undo": {
      if (state.past.length === 0) return state;
      const previous = state.past[state.past.length - 1];
      return {
        past: state.past.slice(0, -1),
        present: previous,
        future: [state.present as Document, ...state.future],
      };
    }
    case "redo": {
      if (state.future.length === 0) return state;
      const [next, ...rest] = state.future;
      return { past: [...state.past, state.present as Document], present: next, future: rest };
    }
    default:
      return state;
  }
}

export const API = "/api";

async function patch(kind: "document" | "layout" | "retranslate", id: string, body: unknown): Promise<Response> {
  const url =
    kind === "document"
      ? `${API}/jobs/${id}/document`
      : kind === "layout"
        ? `${API}/jobs/${id}/layout`
        : `${API}/jobs/${id}/retranslate`;
  return fetch(url, {
    method: kind === "document" ? "PATCH" : "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function useEditor(jobId: string | null) {
  const [history, dispatch] = useReducer(reducer, initial);
  const document = history.present;
  const saveTimer = useRef<number | null>(null);

  const load = useCallback(
    async (id: string) => {
      const response = await fetch(`${API}/jobs/${id}/document`);
      if (!response.ok) return;
      dispatch({ type: "load", document: (await response.json()) as Document });
    },
    [],
  );

  useEffect(() => {
    if (jobId) void load(jobId);
  }, [jobId, load]);

  const persist = useCallback(
    (next: Document, layers: Partial<Layer>[]) => {
      if (!jobId) return;
      if (saveTimer.current) window.clearTimeout(saveTimer.current);
      saveTimer.current = window.setTimeout(() => {
        void patch("document", jobId, { register: next.register, numerals: next.numerals, layers });
      }, 350);
    },
    [jobId],
  );

  const update = useCallback(
    (mutate: (draft: Document) => void, layers: string[] = []) => {
      if (!document) return;
      const next = cloneDocument(document);
      mutate(next);
      dispatch({ type: "commit", document: next });
      persist(
        next,
        layers.map((id) => {
          const layer = next.layers.find((item) => item.id === id);
          return layer
            ? {
                id,
                box: layer.box,
                action: layer.action,
                arabic: layer.arabic,
                font_family: layer.font_family,
                font_size: layer.font_size,
                color: layer.color,
                visible: layer.visible,
                locked: layer.locked,
                z: layer.z,
              }
            : { id };
        }),
      );
    },
    [document, persist],
  );

  const layout = useCallback(
    async (layerId: string) => {
      if (!jobId) return;
      const response = await patch("layout", jobId, { layer_id: layerId });
      if (!response.ok) return;
      const payload = (await response.json()) as { layer: Layer };
      update(
        (draft) => {
          const index = draft.layers.findIndex((layer) => layer.id === layerId);
          if (index >= 0) draft.layers[index] = payload.layer;
        },
        [layerId],
      );
    },
    [jobId, update],
  );

  const retranslate = useCallback(
    async (layerId: string, register: "egyptian" | "msa") => {
      if (!jobId) return null;
      const response = await patch("retranslate", jobId, { layer_id: layerId, register });
      if (!response.ok) return null;
      const payload = (await response.json()) as { layer: Layer; cost_usd: number };
      update(
        (draft) => {
          const index = draft.layers.findIndex((layer) => layer.id === layerId);
          if (index >= 0) draft.layers[index] = payload.layer;
        },
        [layerId],
      );
      return payload.cost_usd;
    },
    [jobId, update],
  );

  const commit = useCallback(
    (mutate: (draft: Document) => void, layers: string[] = []) => {
      update(mutate, layers);
    },
    [update],
  );

  return useMemo(
    () => ({
      document,
      canUndo: history.past.length > 0,
      canRedo: history.future.length > 0,
      undo: () => dispatch({ type: "undo" }),
      redo: () => dispatch({ type: "redo" }),
      commit,
      layout,
      retranslate,
      reload: () => (jobId ? load(jobId) : Promise.resolve()),
    }),
    [document, history.past.length, history.future.length, commit, layout, retranslate, jobId, load],
  );
}
