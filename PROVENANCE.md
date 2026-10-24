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

| goal2/engine/original_match/README.md | diegoami/goal2-archaeology | 424d5998076da1e4efc399c2715689ddb44d3e1a | F004, F010, F013, F014, F018, F020, F023, F026, F027, F028, F029, F030; #250, #252 | 2026-10-17 |
| goal2/engine/original_match/__init__.py | diegoami/goal2-archaeology | 424d5998076da1e4efc399c2715689ddb44d3e1a | F004, F010, F013, F014, F018, F020, F023, F026, F027, F028, F029, F030; #250, #252 | 2026-10-17 |
| goal2/engine/original_match/assets.py | diegoami/goal2-archaeology | 424d5998076da1e4efc399c2715689ddb44d3e1a | F004, F010, F013, F014, F018, F020, F023, F026, F027, F028, F029, F030; #250, #252 | 2026-10-17 |
| goal2/engine/original_match/build.py | diegoami/goal2-archaeology | a1067ba0df7ba9c7644f36e648d897b76c7697f8 | F004, F010, F013, F014, F018, F020, F023, F026, F027, F028, F029, F030; #250, #252; T85/#396 mutable-byte correction | 2026-10-24 |
| goal2/engine/original_match/check.py | diegoami/goal2-archaeology | 424d5998076da1e4efc399c2715689ddb44d3e1a | F004, F010, F013, F014, F018, F020, F023, F026, F027, F028, F029, F030; #250, #252 | 2026-10-17 |
| goal2/engine/original_match/example.py | diegoami/goal2-archaeology | 424d5998076da1e4efc399c2715689ddb44d3e1a | F004, F010, F013, F014, F018, F020, F023, F026, F027, F028, F029, F030; #250, #252 | 2026-10-17 |
| goal2/engine/original_match/image.py | diegoami/goal2-archaeology | 424d5998076da1e4efc399c2715689ddb44d3e1a | F004, F010, F013, F014, F018, F020, F023, F026, F027, F028, F029, F030; #250, #252 | 2026-10-17 |
| goal2/engine/original_match/machine.py | diegoami/goal2-archaeology | 424d5998076da1e4efc399c2715689ddb44d3e1a | F004, F010, F013, F014, F018, F020, F023, F026, F027, F028, F029, F030; #250, #252 | 2026-10-17 |
| goal2/engine/original_match/match.py | diegoami/goal2-archaeology | 424d5998076da1e4efc399c2715689ddb44d3e1a | F004, F010, F013, F014, F018, F020, F023, F026, F027, F028, F029, F030; #250, #252 | 2026-10-17 |
| goal2/engine/original_match/screens.py | diegoami/goal2-archaeology | 424d5998076da1e4efc399c2715689ddb44d3e1a | F004, F010, F013, F014, F018, F020, F023, F026, F027, F028, F029, F030; #250, #252 | 2026-10-17 |
