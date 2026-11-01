# Mascot v2 in the product (needs owner approval)

New branch from current `main`; does not touch PR #239 or video assets.

- `frontend/src/MascotV2.tsx`: inline `assets/mascot/naqsh-v2.svg`, decorative `aria-hidden`, fixed size, hover plays `wave-hello`.
- `StateIllustration`: loading→thinking, empty→idle, export success→happy, error→sad.
- Header mascot 44 px, hover wave; never overlays the canvas; no new dependencies.
- Disable: `?mascot=off` or `VITE_MASCOT=off` (both verified: 0 nodes).
- Palette is the current Vectr/rose palette; no `#5B6CFF` reintroduced.

## Gates

| Gate | Result |
|---|---|
| pytest | **90 passed** |
| typecheck | pass |
| build | pass |
| demo path Playwright | pass; ZIP 9,337,550 bytes; no console errors; 61.5 s |
| axe | home 0, editor 0 |
| `?mascot=off` | 0 nodes |
| `VITE_MASCOT=off` build | 0 nodes |
| screenshots | `L:\naqsh-review\mascot-product-v2\` 1440/1920 idle, wave, thinking, happy, sad |

Screenshots are evidence only; **no visual approval is claimed**. PR is unmerged and labeled
`needs owner approval`. No v1.1 tag.
