# Mascot product integration (needs owner approval)

Branch starts at tag 1.0, then merges current main (palette + mascot assets).

- rontend/src/Mascot.tsx: inline SVG, decorative (ria-hidden), fixed box, hover wave.
- StateIllustration maps loading→thinking, empty→idle, export success→happy, error→sad.
- Header mascot waves on hover; 44 px; no canvas overlay.
- Disable: ?mascot=off or build with VITE_MASCOT=off (both verified: 0 mascot nodes).
- No new dependencies; no pipeline changes.

## Gates (run in this branch)

| Gate | Result |
|---|---|
| pytest | **89 passed** |
| typecheck | pass |
| build | pass (282.96 kB JS) |
| demo path Playwright | pass; ZIP 9,337,544 bytes; no console errors; 61.8 s |
| axe | home 0, editor 0 |
| screenshots | L:\naqsh-review\mascot-product\ 1440/1920: idle, wave, thinking, happy, sad |
| ?mascot=off | 0 nodes |
| VITE_MASCOT=off build | 0 nodes |

Screenshots are evidence only; **no visual approval is claimed**. The PR is intentionally
unmerged and labeled 
eeds owner approval. No v1.1 tag.
