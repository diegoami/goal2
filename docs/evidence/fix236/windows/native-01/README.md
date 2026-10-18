# Fixed-source native Windows watched-viewer acceptance

[confirmed: host-receipt.json, native-1.log, native-2.log] Main executed the actual
fixed product at dfed1519af51dcb105d2526621eec9b313dd4b83. Each scale passed13
corrected deterministic tests and the unchanged original Qt acceptance assertions,
with only frames=True/default60fps mode and observational capture wrappers added.
Both genuine matches compare complete state/Memory/bothRNG/history/events/ratings/
MOTM, Save/Resume/repeat and ownership protections to independent direct originals.
Frames4439/4830 publish after final rendered acknowledgements4438/4829 at both
scales. Callbacks are empty; owned widgets/processes/streams/folders are closed.

[confirmed: observations/scale-1/report.json, observations/scale-2/report.json]
Qt's actual ratios are1/2; SDL independently reports Windows driver,1000×720
surface/window and DPI96 at both scales. SDL is not claimed to scale from the Qt
setting. PNGs are new rebuild Qt/SDL captures, never original-game image assets.

[confirmed: collection-receipt.json] Collection rehashed all176 native/current
source files,566 original/private-archive dependency files and both wheel inputs,
three resource files and four protected launcher/save/data files. All match main's
receipt. Only new observations, wrappers and safe JSON/log metadata are tracked;
private runtimes, original assets and saves remain outside git and unchanged.
The main runner is retained for audit, not for reviewer execution.

[designed] Review audit command (from the review checkout with main-staged cache):

```text
python3 -B .cache/main-native-proof-check.py --expected-receipt-sha256 454bbb4a4bcd2bfc2a951a08b3ddda63c988d77eb8051263096eef25d028dd0a
```

[confirmed: independently held main-original receipt SHA256]
454bbb4a4bcd2bfc2a951a08b3ddda63c988d77eb8051263096eef25d028dd0a is supplied
externally in reviewer input. The helper requires it explicitly, checks both
tracked host receipt and separately staged main-original bytes, then validates
source checkpoint/current source identity, evidence-only carry, reports, captures,
logs, dependency/resource/protected metadata and inventory. This is an audit of
main's retained native execution; it does not pretend the reviewer reran Windows.
The authoritative native original and source archive remain retained by main.

[designed] The collector-time helper/receipt and initial inventory are retained
as separate snapshots. The final helper adds canonical original-result and live
SDL checks; proof-final-receipt.json binds its bytes before the first audit.
