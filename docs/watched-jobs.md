# Watched process bridge

[designed: T65] `goal2.game.watched_jobs.WatchedJobs(owner)` is a headless,
local-process bridge. The owner supplies `state`, `template_bytes` and
`view(candidate)`, as for T64. Keep one bridge for the owner's lifetime and close
it when leaving that owner. It imports neither Qt nor Pygame and starts no server.

```python
jobs = WatchedJobs(owner)
token = jobs.start(fixture)
# From the caller's event loop:
for event in jobs.poll(token):
    show(event)
if not jobs.busy:
    completed = jobs.outcome
# On cancellation or application shutdown:
jobs.close()
```

[designed] `start` snapshots the accepted T64 job and launches a local Python
child. The child prepares its private input and uses the shared watched driver.
The driver's private observer sends each event as consumed, before guest execution
continues. Original decisions use `Match.answer()` with no edits; unsupported
contexts, explicit refusals and immediate repeated decisions fail. Intervening
guest events distinguish later same-minute injury notices. No completed transcript
is replayed as live progress. The public synchronous friendly API remains intact.

[designed] `poll(token)` returns newly observed events in order. Each call reads at
most 64 KiB and parses at most 32 length-prefixed JSON records. A partial record
waits for more bytes; frames over 8 MiB fail. Completed Memory is compressed for
transport and decompressed with a 32 MiB ceiling, preserving opaque bytes. Input
uses the existing explicit-data session-save encoding; IPC executes no serialized
Python objects. These bounds limit work per call, not elapsed response time.

[designed] Full time is a presentation event, not completion. Publication waits
for the child's successful exit, an exactly matching complete live transcript and
T64's complete-result, input, Memory/RNG and tail checks. `outcome` becomes available
only after successful publication. Repeated reads/actions after consumption fail;
reads never start matches. A second bridge on the same owner or second in-flight
start is refused. The owning caller should pass the token returned by `start` to
every poll/cancel action.

[designed] Active state/template replacement or mutation invalidates the job.
Failures preserve the active state and both seeds. A failed job consumes its token
and permits a fresh start. Cancellation requires the current active token, so a
stale action cannot cancel a newer job. Close/cancel terminate only the owned
process, wait up to 0.5 seconds, then kill and wait up to 0.5 seconds. The private
mode-0700 temporary directory and local IPC files live until that process is
reaped; no input/result file is a saved game publication.

[designed] The caller receives actionable errors for missing optional runtime,
guest refusal/no-progress, unexpected exit, malformed/truncated IPC and stale
ownership. The worker uses the caller's Python interpreter; install the optional
runtime using the instructions in [watched kit acceptance](watched-kit-acceptance.md).
Diagnostic seed/delay/draw-recording options are explicit `start` keyword arguments.
Stage-1 workers accept friendly fixtures only and expose no in-play controls.

[designed] Acceptance is `python3 -m unittest goal2.tests.test_watched_jobs -v`.
The suite compares real seeds 257 and 70 for countries7/19, fixture21/year0,
captain0, no requested substitutions, delay0 and draw recording enabled. It checks
the complete synchronous result, ordered events, Memory and both seeds, and prints
measured worker time without a hardware-dependent performance assertion. Retained
attempts and controls are under [task evidence](evidence/T65/).
