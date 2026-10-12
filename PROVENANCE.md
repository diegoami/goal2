# Provenance

Every file under `goal2/engine/` is a byte-copy from `goal2-archaeology`, pinned here. Re-vendoring
is deliberate: a new row (or an updated commit) records it, and the source commit must exist on
`goal2-archaeology`'s `main`. Vendored files are never edited in this repository (CLAUDE.md rule 18).

| File | Source repo | Source commit | Findings it rests on | Vendored |
| --- | --- | --- | --- | --- |
| goal2/engine/quick_engine.py | diegoami/goal2-archaeology | 8760df9 | F012, F004, F006 | 2026-10-12 |
| goal2/engine/savestate.py | diegoami/goal2-archaeology | 8760df9 | F001 | 2026-10-12 |
| goal2/engine/players.py | diegoami/goal2-archaeology | 8760df9 | F002, F007 | 2026-10-12 |
