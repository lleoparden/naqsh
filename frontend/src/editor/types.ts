export type Layer = {
  id: string;
  kind: "text" | "cover";
  type: string;
  action: string;
  source_text: string;
  arabic: Record<string, string>;
  box: [number, number, number, number];
  font_family: string;
  font_size: number;
  lines: { text: string; size: number; x: number; baseline: number; width: number; height: number }[];
  align: string;
  color: [number, number, number];
  z: number;
  visible: boolean;
  locked: boolean;
  strategy: string;
  fill: number[];
};

export type Document = {
  id: string;
  width: number;
  height: number;
  register: "egyptian" | "msa";
  numerals: "latin" | "arabic-indic";
  images: { plate: string; composite: string; output: string; source: string };
  layers: Layer[];
};

export type History = { past: Document[]; present: Document | null; future: Document[] };

export const FONTS = ["tajawal", "tajawal-bold", "naskh", "amiri"] as const;
export const FONT_LABELS: Record<string, string> = {
  tajawal: "Tajawal",
  "tajawal-bold": "Tajawal Bold",
  naskh: "Noto Naskh",
  amiri: "Amiri",
};

/** Arabic sample shown beside each font option and under the picker. */
export const FONT_SAMPLES: Record<string, string> = {
  tajawal: "أهلاً بالعالم",
  "tajawal-bold": "أهلاً بالعالم",
  naskh: "أهلاً بالعالم",
  amiri: "أهلاً بالعالم",
};

export function cloneDocument(document: Document): Document {
  return JSON.parse(JSON.stringify(document)) as Document;
}

export function layerById(document: Document | null, id: string | null): Layer | null {
  if (!document || !id) return null;
  return document.layers.find((layer) => layer.id === id) ?? null;
}
