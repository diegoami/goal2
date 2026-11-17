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
alone does not establish the live outside-match SELECT TEAM→Ins refusal.
The bounded native acquisition below records that separate evidence without
another qualifying campaign or an artificial finals-flag change.

## Native refusal and standalone comparison

[confirmed: DOSBox-X2024.03.01 acquisition, E031 G4B.GL; F031]
The unchanged G4B save loads at Holland's World Cup2030 manager menu, before
Germany. The actual keys are title **Y**, **Enter** to load, four **Down** keys,
**Enter** for SELECT TEAM, **Ins**, **Enter** to acknowledge and **Esc** to the
manager menu. The original displays *cannot alter squad during finals*. Its
current manager is1 and his existing finals flag is1.

[confirmed: actual PyPy versus that original key trace]
The copied native assistant returns the same finals refusal, no recruits and
exactly equal complete player/country/manager/game records, ordered20/80 IDs
and RNG. Original SELECT TEAM preparation is included; the refusal and ordinary
acknowledgement preserve all those records. The PyPy helper positively denies
Unicorn and GOAL.EXE reads. No original-owned record is patched.

The public [native receipt](../../measurements/725-retained-finals/native-v1.json)
contains source, producer, input and output hashes, every key/screen digest and
per-record equality hashes. Original savestates, full screen text, driver events
and G4B.GL stay in the owner's private artifact folder as
`T183-finals-G4B-native-v1.zip`. Its normalized manager-boundary fixture is
`T183-finals-G4B-manager-v1.g2core`; both hashes are in the receipt.

Reproduce the actual acquisition with a prepared archaeology clone and a new
output directory (existing acquisitions are never overwritten):

```sh
rclone copyto goal2drive:goal2-archaeology/390-existing-states-20261023/G4B.GL .cache/G4B.GL
python tools/prove_assistant_finals.py --archaeology "$GOAL2_ARCHAEOLOGY" --save .cache/G4B.GL --out .cache/finals-new-acquisition
```

The repeatable original-key/PyPy regression uses the pinned private fixture:

```sh
python tools/artifacts.py pull T183-finals-G4B-manager-v1.g2core
python -m unittest goal2.tests.test_best_twenty_finals_t183d -v
```

[designed: parent T183/#594]
This supplies the missing genuine finals refusal context requested by
[archaeology #725](https://github.com/diegoami/goal2-archaeology/issues/725).
It does not extend the opening-career UI projection into later seasons, replace
the native held-season window work, or complete the parent's full m3 acceptance.
