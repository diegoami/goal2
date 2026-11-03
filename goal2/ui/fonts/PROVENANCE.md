# The new window's font

[designed: owner, 2026-11-03, #526, #536] The new window (`goal2/ui`, docs/ui.md) draws every screen in a blocky
VGA-style font, the design's ([docs/design/ui-2026-11](../../../docs/design/ui-2026-11/README.md#3-rules-for-the-whole-ui)).
These are the same files as the mockups' copy in
[docs/design/ui-2026-11/mockups/fonts/](../../../docs/design/ui-2026-11/mockups/fonts/PROVENANCE.md), copied
unchanged into the package so that the window loads the font from package data, never from a system install, and
so that the licence ships beside it in the wheel and the portable build.

| File | What it is | Source | Licence |
| --- | --- | --- | --- |
| `PxPlus_IBM_VGA_8x16.ttf` | "PxPlus IBM VGA 8x16", a pixel-outline TrueType remake of the IBM VGA 8×16 text font, by VileR | The Ultimate Oldschool PC Font Pack v2.2 (2020-11-21), <https://int10h.org/oldschool-pc-fonts/>, file `oldschool_pc_font_pack_v2.2_FULL.zip` (SHA-256 `21b3c0a3770ef0afc46564760613d7b078f4fcc9ed93db4b829a440b68822e08`), member `ttf - Px (pixel outline)/PxPlus_IBM_VGA_8x16.ttf` | Creative Commons Attribution-ShareAlike 4.0 International ([LICENSE.TXT](LICENSE.TXT), copied unchanged from the pack) |

The font file is the pack's, unchanged: SHA-256
`c99fb740581471c2bd239a200c9f7a6c12f60a7099b0f0af795e405281bc2c5f`. Attribution: "PxPlus IBM VGA 8x16" by
VileR, The Ultimate Oldschool PC Font Pack, int10h.org, CC BY-SA 4.0.

It is not the original game's font: no byte of GOAL.EXE or of any GOAL2 file is in it (CLAUDE.md rule 14).
