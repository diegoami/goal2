# Original pitch Insert audit correction

[confirmed: original0791:9372, original0791:ED8A; named seg0791_08/13 and raw seg0791_15/23 at archaeology b0c0fae2] The pitch dispatch has no Insert branch. Its original runtime key0xB6 leaves the automatic-replay byte at [DS:A923]+0x41 unchanged; the match menu ED8A toggles that byte for0xB6. E031C37 already places the toggle on the match menu.

probe.py executes the original9372 dispatch and original pushed-key read on an isolated E006 image for both starting replay values. Only the keyboard-ready service214B:0723 returns true; no game branch is replaced. Positive Right0xAF controls change speed2→1. All four calls consume the key, preserve the replay byte and return through nearret withSP+2. No original bytes/owner saves are included. This is a declared synthetic key fixture, not a natural complete match. The initial external BIOS-interrupt harness calibration failed on an unusable E006 IVT target and was replaced before these acceptance controls; it is not a pass. Its original script/error is retained in the owner keep/insert-audit evidence.

Reproduce with the prepared private fixture:

`python measurements/T191/insert-audit/probe.py --fixture .cache/e006-r0001-main.sav --out /tmp/insert-receipt.json`

The earlier T191 matrix's suspected pitch-toggle gap is corrected by this bounded finding. No application binding or game rule changes are justified. Replay timing, goal questions and full UI journeys retain their separate acceptance requirements.
