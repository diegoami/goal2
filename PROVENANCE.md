# Provenance

Every file under `goal2/engine/` is a byte-copy from `goal2-archaeology`, pinned here. Re-vendoring
is deliberate: a new row (or an updated commit) records it, and the source commit must exist on
`goal2-archaeology`'s `main`. Vendored files are never edited in this repository (CLAUDE.md rule 18).

| File | Source repo | Source commit | Findings it rests on | Vendored |
| --- | --- | --- | --- | --- |
| goal2/engine/quick_engine.py | diegoami/goal2-archaeology | 8760df9 | F012, F004, F006 | 2026-10-12 |
| goal2/engine/savestate.py | diegoami/goal2-archaeology | 8760df9 | F001 | 2026-10-12 |
| goal2/engine/players.py | diegoami/goal2-archaeology | 8760df9 | F002, F007 | 2026-10-12 |
| goal2/engine/energy.py | diegoami/goal2-archaeology | 0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb | F018, F007 | 2026-10-16 |
| goal2/engine/confidence.py | diegoami/goal2-archaeology | 0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb | F019 | 2026-10-16 |
| goal2/engine/morale.py | diegoami/goal2-archaeology | 0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb | F020 | 2026-10-16 |
