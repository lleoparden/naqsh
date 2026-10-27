# Editor click-through checklist (human)

For the owner to run by hand on the comic and the menu. Tick each box; if a step fails,
write the step number in the defect log at the bottom with a screenshot.

Run with the backend on `DEMO_MODE=0` and a page already localized (open it from the
result screen, or `/?job=<id>`). Browser zoom 100%, window at least 1500×950.

## Comic — `01-comic-flat` (3 regions)

| # | Step | Expected result | Pass |
|---|---|---|---|
| 1 | Open the job in the editor from the result screen | Canvas shows the plate, three Arabic text layers, and the layer list has 3 entries | ☐ |
| 2 | Click `t1` in the layer list | The region is selected (dashed box) and the side panel shows its Arabic text | ☐ |
| 3 | Click the canvas text of another region | Selection moves to that region | ☐ |
| 4 | Edit the Arabic in the textarea and press Tab | The canvas text changes; wait ~1 s and reload — the new text persists | ☐ |
| 5 | Switch the register picker to MSA | Text still renders; the panel edits the MSA register | ☐ |
| 6 | Click Re-translate on the selected region | Arabic changes (or is confirmed), a cost (≈$0.001) appears, no error | ☐ |
| 7 | Change the font (Tajawal → Noto Naskh) | Text reflows and stays inside its box | ☐ |
| 8 | Change the size by ±10% | Text re-fits; no overflow outside the region box | ☐ |
| 9 | Change the colour | Text colour changes immediately | ☐ |
| 10 | Toggle Translate → Skipped on one region | That region's Arabic disappears from the canvas | ☐ |
| 11 | Drag the selected region's box | Box moves; text re-centres and stays inside | ☐ |
| 12 | Drag the resize handle | Box grows; text re-fits without clipping | ☐ |
| 13 | Press Ctrl+Z twice | Drag and resize are undone, one step each | ☐ |
| 14 | Press Ctrl+Y twice | Both changes are reapplied | ☐ |
| 15 | Reload the page | Box position, text and skip state persist | ☐ |
| 16 | Click Cover patch, drag a rectangle on the plate | A flat patch appears and becomes a layer in the list | ☐ |
| 17 | Toggle a layer's eye | Its text/patch hides and shows | ☐ |
| 18 | Lock a layer and try to drag it | The layer cannot be moved | ☐ |
| 19 | Move a layer up/down with the z arrows | Draw order changes on the canvas | ☐ |
| 20 | Switch numerals Latin → Arabic-Indic | Prices/numbers in `price` layers switch digits; other text is unchanged | ☐ |
| 21 | Drag the before/after slider | Source and result blend across the canvas | ☐ |
| 22 | Click SVG | Downloads; open it in a browser — Arabic renders, text is selectable | ☐ |
| 23 | Click SVG outlined | Arabic renders with no text elements (paths only) | ☐ |
| 24 | Click PNG | Image is exactly the source size (1280×1920) | ☐ |
| 25 | Click Bundle (ZIP) | Contains both SVGs, plate.png, fonts + OFL licences, README | ☐ |

## Menu — `03-menu-paper` (16 regions)

| # | Step | Expected result | Pass |
|---|---|---|---|
| 1 | Open the job in the editor | Canvas shows 16 text layers; prices are separate `price` layers | ☐ |
| 2 | Select a menu-item layer and a price layer in the list | Side panel switches between them; price layer shows its numerals | ☐ |
| 3 | Edit an item's Arabic and reload | New text persists | ☐ |
| 4 | Switch register and re-translate one item | Arabic changes for MSA; cost shown | ☐ |
| 5 | Change font and size on one item | Fits inside the item box | ☐ |
| 6 | Toggle one layer to Skipped | Only that layer's Arabic disappears | ☐ |
| 7 | Drag one box, resize another | Both re-fit; no overlap with neighbours | ☐ |
| 8 | Ctrl+Z / Ctrl+Y | Undo and redo behave as one step per action | ☐ |
| 9 | Reload | All edits persist | ☐ |
| 10 | Add a cover patch over a price | Patch layer appears above the plate | ☐ |
| 11 | Toggle eye, lock, and z-order | All three behave | ☐ |
| 12 | Numerals toggle | Digit style changes in price layers only | ☐ |
| 13 | Before/after slider | Blends source and result | ☐ |
| 14 | Export SVG | Opens; text selectable; Arabic shaped and RTL | ☐ |
| 15 | Export outlined SVG | Paths only; visually identical at 100% | ☐ |
| 16 | Export PNG | 1280×1920 | ☐ |
| 17 | Export ZIP | Both SVGs, plate, 4 fonts, 3 OFL files, README | ☐ |
| 18 | Open `export.svg` in Inkscape or Figma | Layer groups appear (plate, covers, text layers, original reference); each text layer is selectable and editable | ☐ |
| 19 | Install the bundled fonts, reopen the SVG | Arabic matches the outlined variant; line breaks unchanged | ☐ |
| 20 | In the app, open the exported SVG's text layer and edit one word | The word can be edited with Arabic shaping intact | ☐ |

Stop at step 20; the remaining checks are the same as comic steps 17–25 already
covered.

## Defect log

Screenshot each defect (full window), name the file `defect-<page>-<step>.png`, keep it
outside the repo, and fill one row per defect.

| Page | Step | What happened (expected vs actual) | Screenshot file | Severity (blocks demo / annoying / cosmetic) |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

## What "pass" does not mean

Ticking a box means the interaction behaved as described, not that the output looks
good. Quality is judged separately; note anything ugly in the defect log with severity
"cosmetic".
