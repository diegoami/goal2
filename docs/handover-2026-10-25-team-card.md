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
for the reviewer, per archaeology process 14. This upstream session does not merge goal2.
3. In a separately scoped consumer task, deliberately vendor the reviewed decoder,
record source/hash in provenance, and change only the manager reader: read the initial
byte and exactly 13 surname-record bytes; call manager_text. Validate manager 0..134.
Use current memory (human edits), not original GOAL.DAT. Add independent Vogts,
shorter-length, interior-NUL, max-width and glyph tests. Avoid global pstr changes.
4. Do not claim Live adoption or a Windows rendering regression pass from this delivery.

Owner request: resolve the visible TEAM-card defects faithfully. Both manager-name and Status/Skill deliveries are complete upstream; their contracts follow
below. Remaining placeholder evidence is inventoried separately in archaeology#432.

## Country Status and Skill (archaeology428/T94)

Merged source: diegoami/goal2-archaeology@aec8ddd1d896caef686aceda6f90b8f79ab0fbe6, PR431. See that PR's independent
review and final-head CI receipts. F035 remains proposed: isolated original-code
execution is static-adjacent, not independent behavioral corroboration.

runtime/decoders/country.py SHA256
d2ab97927ecd7ae269f9351f7244dde9eee56af41ffa774a34f520428c4c7b3a;
manager dependency hash remains the one above.

Actual original full TEAM templates resolve the old misleading routine names:
Status=country rank-derived label (Germany giant), Skill=selected manager ability
(Germany eclectic). Both snapshots: rating 126, manager 12 ability 126. Albania is
poor/very bad; Sweden major/exceptional; Yemen AR very small/negligible.
Original r1 receipt's semantic JSON keys were reversed, while its raw panel rows
were correct; preserve r1 and consume corrected r2/r3. No receipt was overwritten.

Evidence: 256 genuine country/state pairs, six full original panels, all 128 normal
country rating values and all 256 manager byte values; four synthetic Germany/human
manager contexts preserve Status giant while Skill changes unknown/none/eclectic/ok.
Seven independent country tests and eleven deliberate mutants; five manager tests.
Source/input/producer/helper hashes are in notes/428/original-r3.json. No original
binary/data/save/screenshot bytes are delivered.

Consumer instructions: read the full pinned docs/requests/428-country-labels.md
and F035. Read current 191-byte country record at far(A917)+191*c; m=country+0x2E;
read current 3-byte record at far(A91F)+3*m. Provide exact read_ds/read_code callbacks
and call team_labels. Forward status and skill only; preserve None for manager 0,
unknown for ability 0, unsigned byte lookup without invented clamp. Do not substitute
player-card skills, team bars, the country number or manager confidence byte+2.
Deliberately vendor both reviewed modules and pin both hashes in a separate consumer
task; add independent original-label, boundary, sentinel and manager-context checks.

Remaining ranking-top/strips/team-skills/performance/characteristics gaps have
partial accepted evidence, not complete display contracts. See archaeology#432
and the evidence audit; no extra implementation is authorized silently.

Reconcile this two-file docs-only branch with current assumptions.md preserving
all Live cells. Open a docs-only PR and ask the owner for the reviewer. Archaeology
does not merge goal2 or change runtime/vendor/UI/backend in this delivery.
Owner's two upstream requests are delivered; downstream adoption is a separate task.
