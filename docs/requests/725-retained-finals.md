# Retained finals candidates for archaeology #725

[confirmed: read-only hash/header inventory, 2026-11-17]
The existing private G13/G16 delivery already contains three candidate saves
after Holland's genuine World Cup group fixtures. The current manager's saved
finals flag is1 in G4B.GL, G4C.GL and G4D.GL; G4A.GL, at the start of the finals
year before those fixtures, is0. The complete scalar observations, source pins
and acquisition paths are in
[metadata-v1.json](../../measurements/725-retained-finals/metadata-v1.json).

| Save | Existing campaign observation | Current manager | Finals flag |
| --- | --- | --- | --- |
| G4A.GL | Holland qualified; finals year begun | 1 | 0 |
| G4B.GL | Beat Chile and Zambia; before Germany | 1 | 1 |
| G4C.GL | Group completed; before last16 against Belgium | 1 | 1 |
| G4D.GL | Beat Belgium on penalties in the last16 | 1 | 1 |

The existing source is E031's
[save table](https://github.com/diegoami/goal2-archaeology/blob/3cf746abec51dd11dadc695a65f4fb32df7701c8/experiments/E031-play-the-game/out/saves.tsv).
The pinned
[390 inventory](https://github.com/diegoami/goal2-archaeology/blob/aba7487749f6a122bf78d2403750b27a8c9e9038/notes/390/inventory.json)
supplies hashes and private Drive paths. Local copies were found under
`.cache/goal2-archaeology/390-existing-states-20261023/`; all four hashes and
169553-byte lengths match that inventory.

[confirmed: original1771:027B, F031] The original serializes22 blocks. Summing
the first12 lengths places the270-byte game block at file offset129899.
Its current manager is byte1; the finals flag is byte`0x13 + manager`.
The JSON retains all22 lengths, allowing an independent read-only recheck.

[derived: F031 and the existing E031 provenance] G4B is a strong bounded
acquisition candidate for the requested natural finals context. This inventory
does not establish the live outside-match SELECT TEAM→Ins refusal. That native
journey, ordinary acknowledgement and source/key trace still need recording;
[archaeology #725](https://github.com/diegoami/goal2-archaeology/issues/725)
remains open. The existing campaign trace and retained saves avoid another
qualifying campaign or an artificial finals-flag change.
