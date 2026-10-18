# T82 independent pitch frame API and evidence

[designed: T82] `WatchedJobs.start(fixture, frames=True)` opts a friendly match
into presentation observation. Default `frames=False` preserves T65 completion;
T66 text Watch and T51/T80 competitive drivers continue using the default. No
engine vendor code or original resources are changed or committed. Production
uses the accepted [T81 contract](../T81/README.md), not its evidence-tool module.

[designed] A consumer runs `events = jobs.poll(token)` and delivers those
canonical events before calling `frames = jobs.poll_frames(token)`. Every sample
is a discrete completed original tick; never assign its pose to an earlier
commentary event. `watermark` is the number of canonical events already observed
by the child before that tick. The parent withholds any frame until at least
that many events have been returned by `poll`. Watermarks are nondecreasing.
Frame data never enters `Event`, `WatchedOutcome`, the result or a save.

[designed] After displaying/consuming returned samples, call
`jobs.ack_frames(token, last_consumed_sequence)`. This cumulative acknowledgement
must advance and cannot exceed the last sample actually returned. Merely writing
a journal or finishing the engine does not acknowledge anything. Duplicate,
stale-token, boolean and future acknowledgements are rejected. Acknowledgement
does not poll or swallow events. Continue canonical `poll`; after successful
child exit, full-tail/transcript validation, complete frame drainage, exact tick
count and final acknowledgement, the existing T64 publication runs once.
`engine_complete` distinguishes child/transcript completion from publication;
`busy`, publication ownership and owner `match_pending` remain set until this
gate or cancellation. `outcome` becomes available only on publication. Keep the
last tick visible through terminal events; postmatch teardown is not a sample.

[designed] `cancel(token)` and `close()` release only this bridge's process,
files and pending ownership, including after engine completion while awaiting a
viewer. The desktop save guard continues refusing while `match_pending` is set;
prior saves and state remain unchanged on cancellation or errors. Invalid frame
IPC cancels the owned job. Invalid acknowledgements leave the job pending so a
correct consumer can continue. Do not replace the owner state during a session.

## Version 1 sample

[designed] The separate private length-prefixed JSON frame journal carries
`[token, frame]`. The headless consumer returns dictionaries without Memory or
GameState. Exact keys are:

| Field | Meaning |
| --- | --- |
| `version`, `sequence` | version1, zero-based contiguous tick ordinal |
| `watermark` | causal canonical event count |
| `minute`, `score` | actual tick's event minute and score |
| `subtick`, `threshold`, `remaining` | raw original clock words/threshold byte |
| `selector`, `attack` | signed threshold comparison and original direction table by fixture team |
| `sentinel` | original packed hidden-position word |
| `ball` | `[signed_x, signed_y, hidden]` |
| `players` |22 rows `[global_slot, team, local_slot, current_player_word, signed_x, signed_y, raw_state, hidden]` |

[confirmed: F013/F018/F028; kit424d5998076da1e4efc399c2715689ddb44d3e1a,
T81] Fixed screen coordinates are `[y,x]`; low slots1..11 belong to fixture
second/team1 and high slots12..22 to first/team0. Local slot labels are1..11,
not persistent shirts. Per-frame current player words retain substitutions.
Only the exact packed sentinel suppresses player or ball drawing; raw state is
preserved without guessed lifecycle semantics. All signed byte coordinates are
retained, including positions outside in-play predicates. The half selector
changes attack direction, never fixed screen orientation. Only original tick
stops are samples; original drawing/movement still execute and use their RNG.

## Budgets and slow consumers

[designed] Each frame packet is at most4096 bytes. A journal is at most16MiB
and8192 frames per session. Each `poll_frames` reads at most65536 bytes and
returns at most32 frames; its internal partial-record buffer stays at most
65536+4096 bytes. It does not read another batch while a full record is pending,
including while waiting for a causal canonical watermark. The existing canonical
poll retains its separate64KiB/32-packet budgets. Frame count must equal the
validated original result's tick count before publication.

[designed] The finite journal is lossless for this budget; slow viewers do not
block the engine or cause invented/dropped samples. The fixed on-disk session
budget includes already-consumed samples, since no concurrent file rewriting or
unbounded spool is used. Exhausting any writer budget fails the worker and
cancels publication; an oversized untrusted journal also fails parent reads.
A viewer may finish later than the engine within this budget, or cancel. There
is no timeout that silently publishes an unconsumed presentation.8192 is a
rebuild resource limit, not a universal claim about original match duration.
No renderer or interpolation is included.

## Reproduction and retained receipts

[designed] Use Python3.12+ with the optional watched/desktop dependencies, verified
ignored E006/GOAL.DAT fixtures and `TMPDIR` pointing at a physical `.cache/tmp`.
Use `QT_QPA_PLATFORM=offscreen SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy` on Linux.

```bash
python3 -m unittest goal2.tests.test_watched_pitch_jobs -v
python3 tools/prove_watched_pitch_jobs.py
```

[designed] Run proof controls only when other source readers have finished. They
run a positive synthetic suite, save source bytes, mutate production checks,
require specific assertion failures (never ERROR/import/timeout), and restore
exact bytes in `finally`. Each invocation retains a new `controls-<time_ns>`
directory. No receipt is overwritten. Synthetic cases are labelled separately
from actual original execution; platform and hashes are in control receipts.

[confirmed: T82 focused-01.log] The first13-test run passed both original seeds:
seed257 produced4279 frames/1079 canonical events; seed4660 produced4146/1178.
Full outcomes exactly matched their unsampled baselines. This early receipt
predates expanded raw-oracle, live-read, cancellation and round-trip checks.
[designed] Later focused/regression receipts and a source/validation manifest
record the expanded accepted check set. No Windows execution claim is made.
