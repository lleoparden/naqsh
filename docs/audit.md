# Repository audit — 2026-10-27

Scope: README claims, asset rights, provenance, secrets. Commands are listed so the
audit can be re-run; results are what they returned on this date.

## Secrets

| Check | Command | Result |
|---|---|---|
| Key-like strings in the working tree | `git grep -n -I -E "(LLM_[A-Za-z0-9]{8,}\|ghp_[A-Za-z0-9]{20,}\|sk-[A-Za-z0-9]{20,}\|Bearer [A-Za-z0-9._-]{20,})"` | no matches |
| `.env` ever committed | `git log --all --oneline -- .env` | no commits |
| Key name mentions | `git grep -n "MODEL_API_KEY"` | `.env.example` (empty), config/route code, docs — no values |
| Key prefix mentions in history | `git log --all --oneline -S "LLM_"` | initial scaffold only; the string is documentation (`.env.example`, `docs/api-findings.md`, a test asserting the key never appears in `/api/health`) |
| Health endpoint leak test | `backend/tests/test_health.py` | asserts `LLM_` is absent from the response |

Verdict: **no key material in the working tree or history**. The only key-shaped text
is the documented prefix.

## Provenance (no copied code)

| Check | Result |
|---|---|
| `git grep -in "vectr"` outside README/docs | only `AGENTS.md` and `.ecc/issues/phase-1-setup.md`, both policy statements ("no code copied") |
| Code reuse from the older desktop tool | no Electron, Skia, document-format, compiler, or release files exist here; every source file was added during this event (first commit is the scaffold, dated 2026-10-27) |
| Workflow conventions | re-created for Naqsh (AGENTS.md, `.agents/workflows/`, PR template) |

This is a negative claim and cannot be proven by search alone; what can be checked is
that no such code is present and that the history is a build from an empty scaffold.

## Assets

`ASSETS.md` audit script (every tracked path under `assets/` and `fixtures/` must
appear): it found **25 missing entries — the five `fixtures/demo/` caches** (receipts,
documents, plates, sources, masks). Fixed in this PR: five rows added, each pointing at
the source fixture and the recorded job, with the licence inherited from that fixture.

Fonts: four OFL families with the three licence texts present in `assets/fonts/`
(`OFL-Tajawal.txt`, `OFL-NotoNaskhArabic.txt`, `OFL-Amiri.txt`); both Tajawal weights
cover the same licence file. Public-domain poster: the Commons licence snapshot is in
`assets/generated/fixtures/06-real-pd-poster.json` and referenced from its row.

Still missing / not mine to fix:

- `docs/evidence/` and `fixtures/demo/` screenshots are evidence, not licensed media;
  they are not listed in `ASSETS.md` by design (they are generated from owned runs).
- Repo weight: **101.1 MB tracked** (227 files). The largest items are the eight
  fixtures (3–4 MB each) and the 10.97 MB demo cache. That is the price of demo mode
  replaying real pixels; it is recorded here rather than hidden.

## README

- "What's new" is accurate: new work during the event, no fork/port, rights rule
  stated. It is about provenance, not a feature list, so demo mode and the editor are
  not mentioned there; they are covered in their own sections.
- Repository layout was missing `docs/evidence/` and `fixtures/demo/`. Fixed.

## Gaps that block the submission (owner)

- Manual baseline for the time-saved claim (#9) — the sheet has an empty column.
- At least one live run in the demo video.
- Inkscape/Figma hand-check of `export.svg` (fonts installed) — never verified here.
- resvg comparison was never produced; the SVG render parity was measured in Chrome.
