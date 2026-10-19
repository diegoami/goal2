# New original-game captures made for issue #244

[confirmed: E031 source] Each `M244-G1A` run started the original GOAL2 under archaeology's `experiments/E031-play-the-game/play.py` `PlayDriver`, DOSBox-X 2024.03.01 and a private Xvfb display. Its `workdir` and mounted game copy were under `/tmp/goal2-244-captureN`; no shared emulator, session or desktop was used. The G1A.GL loaded for runs 01–04 is the published E031 checkpoint “Holland, new game 2028, before the first match”, SHA-256 `b6e3c4c14d25543d28e4d5a38a43882c562b3acfe4f8834a7b64183024c6b152`, verified against `experiments/E031-play-the-game/out/saves.tsv` before launch. The ten original release files were verified against archaeology's `artifacts/known.json` set `goal2-67cf27d6`. Run 05 loaded G4C.GL, the published 2030 World Cup last-sixteen checkpoint, SHA-256 `06af479da77db6e1da7847de929bf43531349f2fcddcaeac3ba93e8b16da304d`, checked against the same save register. No original file or savestate is tracked here.

[confirmed: capture logs] Each JSON log records the numbered screenshot and the *single* preceding key action. Each image was rendered from the immediately read savestate, with its text digest, source savestate hash, resulting PNG hash and font source recorded. Those savestates were temporary; a reviewer can check the committed screenshot hash and replay the documented action sequence from the retained G1A release save. These captures are new live evidence, distinct from the manifest-verified E015 reconstructions in `image-provenance.tsv`.

| Run | Logged path | Illustrated branch |
| --- | --- | --- |
| M244-G1A-01 | [capture](captures/m244-g1a-01.json) | title, Y, load-name prompt, Enter to manager |
| M244-G1A-02 | [capture](captures/m244-g1a-02.json) | title/load, Space squad, Down card, Right pool, Down card, Left squad, T individual tactics, Esc twice, T team tactics |
| M244-G1A-03 | [capture](captures/m244-g1a-03.json) | title/load, Down fixture list, Enter, Down selected fixture/watch hint, Esc, Down tournament, Enter, Down group, Esc, Down history, Enter |
| M244-G1A-04 | [capture](captures/m244-g1a-04.json) | G1A player role R/C before/after and position-tactic option |
| M244-G4C-05 | [capture](captures/m244-g4c-05.json) | G4C 2030 World Cup team info, player card, Finals bracket and qualifying groups |

[designed: issue #244] New observations support only their shown key and immediate screen transition. They do not establish every later control or condition. The original guide's E031 claims and reviewed findings are cited separately for those.
