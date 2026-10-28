/**
 * UI chrome strings, English and Arabic.
 *
 * English is the default. Arabic UI strings are a first draft by a non-native
 * copywriter and are marked TODO(native-review) — the owner reviews them before the
 * demo. Content being localized is never routed through here: region translations
 * and the output image are always Arabic.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

export type Lang = "en" | "ar";

const en = {
  brand: "NAQSH · نقش",
  headline: "Turn any page into editable Arabic layers",
  subhead:
    "Arabic-first localization: the model finds the lettering, the plate is repainted, and the Arabic is set right-to-left in the original space.",
  uploadCta: "Choose a page to localize",
  uploadBusy: "Working… {seconds}s — reading, segmenting, repainting, typesetting",
  uploadHint: "PNG, JPEG or WebP · up to 15 MB",
  register: "Arabic style",
  registerEgyptian: "Egyptian colloquial",
  registerMsa: "Modern Standard Arabic",
  registerHint: "Applies to pages you localize from now on.",
  apiConfigured: "API key configured",
  apiMissing: "API key missing in .env",
  backendOffline: "backend offline",
  before: "Before · {width}×{height}",
  after: "After · {ms} ms · ${cost}",
  regions: "Regions · {count}",
  receipt: "Receipt",
  download: "Download PNG",
  sheet: "Before / after sheet",
  footer: "Meta Global AI Developer Hackathon · Build for Your World",
  error: "Something went wrong: {message}",
  stageRead: "read",
  stageSegment: "segment",
  stagePlate: "repaint",
  stageComposite: "align + composite",
  stageVerify: "verify plate",
  stageRetry: "retry plate",
  stageRepair: "repair",
  stageFinalCheck: "final check",
  stageTypeset: "typeset",
  stageSelfcheck: "self-check",
  warnings: "Warnings",
  language: "Language",
} as const;

export type StringKey = keyof typeof en;

// TODO(native-review): short UI Arabic; review tone and phrasing before the demo.
const ar: Record<StringKey, string> = {
  brand: "نقش · NAQSH",
  headline: "حوّل أي صفحة إلى طبقات عربية قابلة للتعديل",
  subhead:
    "تعريب بصري عربي أولاً: يجد النموذج النص، يُعاد رسم الخلفية، ثم تُصفّ العربية من اليمين إلى اليسار في المكان الأصلي.",
  uploadCta: "اختر صفحة لتعريبها",
  uploadBusy: "جارٍ العمل… {seconds} ثانية — قراءة وتقطيع وإعادة رسم وتنسيق",
  uploadHint: "PNG أو JPEG أو WebP · حتى 15 ميجابايت",
  register: "الأسلوب العربي",
  registerEgyptian: "عامية مصرية",
  registerMsa: "الفصحى",
  registerHint: "يُطبَّق على الصفحات التي تترجمها من الآن.",
  apiConfigured: "مفتاح الواجهة جاهز",
  apiMissing: "مفتاح الواجهة غير موجود في .env",
  backendOffline: "الخادم غير متصل",
  before: "قبل · {width}×{height}",
  after: "بعد · {ms} مللي ثانية · ${cost}",
  regions: "المناطق · {count}",
  receipt: "الفاتورة",
  download: "تنزيل PNG",
  sheet: "ورقة قبل/بعد",
  footer: "هاكاثون ميتا العالمي للذكاء الاصطناعي · ابنِ لعالمك",
  error: "حدث خطأ: {message}",
  stageRead: "القراءة",
  stageSegment: "التقطيع",
  stagePlate: "إعادة الرسم",
  stageComposite: "المحاذاة والتركيب",
  stageVerify: "فحص الخلفية",
  stageRetry: "إعادة المحاولة",
  stageRepair: "الإصلاح",
  stageFinalCheck: "الفحص النهائي",
  stageTypeset: "التنسيق",
  stageSelfcheck: "الفحص البصري",
  warnings: "تنبيهات",
  language: "اللغة",
};

const STRINGS: Record<Lang, Record<StringKey, string>> = { en, ar };
const STORAGE_KEY = "naqsh.ui.lang";

const STAGE_KEYS: Record<string, StringKey> = {
  read: "stageRead",
  segment: "stageSegment",
  clean_plate: "stagePlate",
  register_composite: "stageComposite",
  verify: "stageVerify",
  retry: "stageRetry",
  repair: "stageRepair",
  final_check: "stageFinalCheck",
  typeset: "stageTypeset",
  selfcheck: "stageSelfcheck",
};

function readStored(): Lang {
  try {
    // ?lang=ar lets a link (and the screenshot script) open the Arabic chrome
    // without clicking; the stored choice still wins afterwards.
    const requested = new URLSearchParams(window.location.search).get("lang");
    if (requested === "ar" || requested === "en") return requested;
    const value = window.localStorage.getItem(STORAGE_KEY);
    return value === "ar" ? "ar" : "en";
  } catch {
    return "en";
  }
}

export function useLang() {
  const [lang, setLang] = useState<Lang>(readStored);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    try {
      window.localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      /* storage can be blocked; the switch still works for this session */
    }
  }, [lang]);

  const t = useCallback(
    (key: StringKey, vars?: Record<string, string | number>) => {
      let text = STRINGS[lang][key];
      if (vars) {
        for (const [name, value] of Object.entries(vars)) {
          text = text.replaceAll(`{${name}}`, String(value));
        }
      }
      return text;
    },
    [lang],
  );

  const stage = useCallback(
    (name: string) => {
      const key = STAGE_KEYS[name];
      return key ? STRINGS[lang][key] : name;
    },
    [lang],
  );

  return useMemo(() => ({ lang, setLang, t, stage }), [lang, t, stage]);
}
