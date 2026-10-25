# TEAM card evidence delivery — 2026-10-25

## Manager names (archaeology429/T93)

Merged source: diegoami/goal2-archaeology@edab133aace9827afa99c8a4efa04e3586f3c567, PR430. Independent review:
https://github.com/diegoami/goal2-archaeology/pull/430#issuecomment-6401249502
F034 remains proposed; isolated original-code probes are static-adjacent, not behavioral corroboration.

Pure module runtime/decoders/manager.py SHA256
1d4340eb8ab57c65c7d4186390842d769eaaf954ed7f205ca9ad83a3f1bba5bf.
Original formatter/writer exact over 135 genuine manager records and 5 synthetic controls;
5 independent unit tests and 6 deliberate decoder mutants. Full input hashes, original
source hashes and immutable receipts are notes/429/original-r1.json and original-r2.json.
No original binary/data/save/screenshot bytes cross into goal2.

The shipped Vogts surname has Pascal length 6 and an embedded last NUL.
Current Memory.manager_name returns U+0000; original screen-cell projection gives
`B Vogts ` (final blank). Exact screenshot codepoint attribution is unverified.
If the symptom persists, retain the private stopped input and inspect the actual
formatted Unicode codepoints and font/render path; do not guess from a tofu box.

## Goal2 session instructions

1. Read archaeology docs/requests/429-manager-name.md and F034 at the merged pin.
2. Reconcile this two-file docs-only branch against current assumptions.md, preserving
all existing Live cells and concurrent decisions. Open a docs-only PR and ask the owner
for the reviewer, per archaeology process14. This upstream session does not merge goal2.
3. In a separately scoped consumer task, deliberately vendor the reviewed decoder,
record source/hash in provenance, and change only the manager reader: read the initial
byte and exactly 13 surname-record bytes; call manager_text. Validate manager 0..134.
Use current memory (human edits), not original GOAL.DAT. Add independent Vogts,
shorter-length, interior-NUL, max-width and glyph tests. Avoid global pstr changes.
4. Do not claim Live adoption or a Windows rendering regression pass from this delivery.

Owner request: resolve the visible TEAM-card defects faithfully. Archaeology next
processes #428 Status/Skill and inventories evidence for the remaining placeholders.
