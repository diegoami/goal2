# Bounded four-year original-core observation

[derived: the source-bound receipt in docs/evidence/T123/proof.json]
Executed runtime: `279904b6217b057198ffd779e347a3a7aba39556`.
The fresh Holland career starts at stage 2/season 0, title 2028, and reaches stage 2/season 2,
title 2032. The declared owner substitution policy is active throughout. The original
E039/GOAL.DAT hashes, explicit DOS inputs, source files and every relevant runtime hash are
recorded in [the receipt](../../docs/evidence/T123/proof.json).

| Observed quantity | Result |
| --- | --- |
| Prover elapsed time | 1291.245 seconds (about 21 minutes 31 seconds) |
| Policy steps | 845 |
| Round-start operations | 62, including the final next-decision replay probe; not a match count |
| Completed country-history matches | 21 EC and 22 WC |
| Annual saved-machine replays | Four; complete memory/CPU/explicit keys/save/destination equal |
| Input trace | 2442 hash-chained rows; 1003 consumed external keys, including queued boot/name keys |
| Shootout decision operations | One announcement and eleven original order inputs |
| Other observed decision operations | 91 managed substitution notices, four best-place waits, one congratulations wait |

[derived: actual original history readback] Completed history labels are 2027/28 EC and
2029/30 WC. This run's EC record is 11 won, 5 drawn, 5 lost; its WC record is 11 won,
7 drawn, 4 lost, runners-up. The next 2031/32 EC qualifying row is present with zero statistics.
The full actual rows remain in the receipt. These are observations of this input/policy,
not equalities with the different-input E031 g1 scores, qualification or placements.

[derived: preserved failed run and prefix comparison] The first attempt at `9d0142cb`
stopped genuinely at congratulations poll 000E:0515 after 37 round-starts and two annual
replays. It remains a failed receipt in `goal2-keep/T123-first-proof-20261025`. After the
bounded #409 fix, the rerun preserves the initial save, both pre-blocker annual saves and
all 1254 pre-blocker trace rows byte-for-byte. No seed sweep, guest fixture/player edit or
additional acquisition trial was used to reach a preferred result.

[designed: T123 scope] The separate `verify_core_cycle.py` command also passes, checking
committed source/runtime identity, original machine records, input-trace integrity and
independently executing the four annual decisions again. Original-byte initial/annual/final/
trace-end machines, full trace and complete CLI receipts remain private under
`goal2-keep/T123-proof-20261025`. The public report contains hashes and observations only.

This is one declared consumer variant through the original whole-game core. No managed
set-piece selector occurred in the full run; genuine bounded tests separately exercise the
retained corner/goal-kick controls. It does not establish arbitrary menu coverage or supply
unchanged-original inputs for archaeology #400. Independent milestone review and the owner's
Windows playtest remain separate acceptance.
