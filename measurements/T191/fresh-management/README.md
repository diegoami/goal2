# Fresh management and separate-process save audit

[confirmed: application d56e793beebb72f3d7418db0d4bf764d1a4c4091; owner611]
The real offscreen Qt window starts at S02, creates a fresh Denmark career through S03/S04,
and uses ordinary keys for all80pool entries, a two-Enter pool/squad exchange, R/C positions,
four personal and eight team tactics. F7 names a save; F10 cancellation stays, then saved quit exits.
A second OS process uses Start/Continue and asserts equality with the complete changed career,
cancels a proposed save, changes a tactic and discards it through the unsaved-quit question.
A third OS process reloads and compares the complete saved career again.

Linux CPython3.14 and native Windows CPython3.13 runs passed all three phases. Windows uses
its own Temp data/save root and no owner-game input. First Windows attempts failed before career
creation because the source fixture symlink was unavailable over UNC; native-v3 uses actual
hash-verified private copies. The first Linux verify job vanished before producing a log: it is
not counted as a pass; the registered verify-v2 rerun passed. All available raw logs are retained.

The two imported fixture hashes and source hashes are in receipt.json. The fresh campaign is
created by the normal UI using those imported inputs; no model services are mocked and no
prepared career or match packet is injected. Expected-state pickle and named-save data remain
private in the isolated roots and are not committed. Rebuilt screenshots and assertion-only
receipts contain no original-game memory dump. The optional help file was absent, so this
run does not claim help-viewer acceptance.

Reproduce each phase in a separate process with the same explicit target:

```sh
python audit.py /path/to/goal2 /tmp/isolated-goal2-audit create
python audit.py /path/to/goal2 /tmp/isolated-goal2-audit resume
python audit.py /path/to/goal2 /tmp/isolated-goal2-audit verify
```

Use the repository offscreen Qt/SDL environment. Native Windows may pass the verified application
head as argument4 and a real private fixture directory as argument5, avoiding unavailable WSL
symlinks. native-driver.py records the actual source/target used here; adapt its paths for another
computer. No OS input injection, original DOS UI/save-format equivalence, watched match, replay,
season, current-live-card or installed-build completion is claimed. These receipts supplement
T168 and the611matrix; they do not close its complete match/result/save journey.
