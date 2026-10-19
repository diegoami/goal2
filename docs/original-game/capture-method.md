# New original-game captures made for issue #244

[confirmed: E031 source] Each `M244` run started the original GOAL2 under archaeology's `experiments/E031-play-the-game/play.py` `PlayDriver`, DOSBox-X 2024.03.01 and a private Xvfb display. Its `workdir` and mounted game copy were under `/tmp/goal2-244-captureN`; no shared emulator, session or desktop was used. The G1A.GL loaded for runs 01–04 is the published E031 checkpoint “Holland, new game 2028, before the first match”, SHA-256 `b6e3c4c14d25543d28e4d5a38a43882c562b3acfe4f8834a7b64183024c6b152`, verified against `experiments/E031-play-the-game/out/saves.tsv` before launch. The ten original release files were verified against archaeology's `artifacts/known.json` set `goal2-67cf27d6`. Runs 05 and 07 loaded G4C.GL, the published 2030 World Cup last-sixteen checkpoint, SHA-256 `06af479da77db6e1da7847de929bf43531349f2fcddcaeac3ba93e8b16da304d`, checked against the same save register. Run 06 loaded G1E.GL, after Holland's twelve 2028 matches and before the year end, SHA-256 `79678118156f59d6ca7b958b876d2d3ee05b8742d1e0ba10c2d6fb5069e34980`, also checked against the register. No original file or savestate is tracked here.

[confirmed: capture logs] Each JSON log records the numbered screenshot and its preceding action: one key or an explicitly timed wait. No row represents a multi-key burst. Each image was rendered from the immediately read savestate, with its text digest, source savestate hash, resulting PNG hash and font source recorded. Those savestates were temporary; a reviewer can check the committed screenshot hash and replay the documented action sequence from the corresponding retained release save. These captures are new live evidence, distinct from the manifest-verified E015 reconstructions in `image-provenance.tsv`.

| Run | Logged path | Illustrated branch |
| --- | --- | --- |
| M244-G1A-01 | [capture](captures/m244-g1a-01.json) | title, Y, load-name prompt, Enter to manager |
| M244-G1A-02 | [capture](captures/m244-g1a-02.json) | title/load, Space squad, Down card, Right pool, Down card, Left squad, T individual tactics, Esc twice, T team tactics |
| M244-G1A-03 | [capture](captures/m244-g1a-03.json) | title/load, Down fixture list, Enter, Down selected fixture/watch hint, Esc, Down tournament, Enter, Down group, Esc, Down history, Enter |
| M244-G1A-04 | [capture](captures/m244-g1a-04.json) | G1A player role R/C before/after and position-tactic option |
| M244-G4C-05 | [capture](captures/m244-g4c-05.json) | G4C 2030 World Cup team info, player card, Finals bracket and qualifying groups |
| M244-G1E-06 | [capture](captures/m244-g1e-06.json) | G1E end-of-qualifying table, elimination bulletin and next-stage hub |
| M244-G4C-07 | [capture](captures/m244-g4c-07.json) | G4C last sixteen, other matches quick, managed captain, R quick to 0–0, extra time, shoot-out prompt/order |
| M244-G4C-08 | [capture](captures/m244-g4c-08.json) | restored run-07 order screen, eleven numbered picks, first shoot-out kick |

[designed: issue #244] New observations support only their recorded action and immediate screen transition. They do not establish every later control or condition. The original guide's E031 claims and reviewed findings are cited separately for those.

Run 08 restored run 07's private temporary savestate at the shoot-out order screen. Its source SHA-256 was `062e210b612ada967e7b7eb1a27338cdd37c130896ea337a977d05efd045cdca`, screen digest `e7d861296bb822f0544f30e7b8d3fc1c2df1291e127723f346abf78c9d0f4613`. The driver used the same private work/game path and checked matching drive layout and restored screen digest before any order choice. This savestate remains in `/tmp`, not this repository. The eleven Enter actions and subsequent timed waits are individually logged; a wait is an observation of automatic play, not evidence that a key caused it. [confirmed: M244-G4C-07 step 56; M244-G4C-08 steps 0–26]
