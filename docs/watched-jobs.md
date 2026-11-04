# Watched process bridge

[designed: T65] `goal2.game.watched_jobs.WatchedJobs(owner)` is a headless,
local-process bridge. The owner supplies `state`, `template_bytes` and
`view(candidate)`, as for T64. Keep one bridge for the owner's lifetime and close
it when leaving that owner. It imports neither Qt nor Pygame and starts no server.

[designed: owner, 2026-11-03, #527 D3; T160] The match plays in the owner's one engine process
([engine-process.md](engine-process.md)), which the owner's bridges share (`MatchEngine`, held on the owner;
`goal2.desktop.competitive.CompetitiveJobs` is the other bridge). The process starts at the first match and is sent
the game with `open`: once, and again only when the game a match plays (the publication's prepared state and the
template) differs from the last one sent, or the process is new. It ends when the owner's last bridge closes (#417).
One match is attached at a time; the engine's reader thread queues that match's replies and the bridge's polls drain
them, so a reply of a cancelled or replaced match never reaches the next one. [designed: T161] No match runs over
file journals; the per-match workers and their journals were deleted. Today's window's quick friendly (B2,
`goal2/desktop/jobs.py`, `worker.py`) is not a bridge here: it plays the Python stand-in in its own worker, belongs
to today's window and goes with it (T170).

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

[designed] `start` snapshots the accepted T64 job. [designed: T160] When the game must be sent, a thread
encodes it and sends it with `open`; the owner's thread asks the match (`match`) once that is done, or at once
when the engine already has the game. The engine prepares the match and uses the shared watched driver.
The driver's private observer sends each event as consumed, before guest execution
continues. Original decisions use `Match.answer()` with no edits; unsupported
contexts, explicit refusals and immediate repeated decisions fail. Intervening
guest events distinguish later same-minute injury notices. No completed transcript
is replayed as live progress. The public synchronous friendly API remains intact.

[designed] `poll(token)` returns newly observed events in order. [designed: T160] Each call consumes at most 32
of the match's queued replies. The pipe's packets are bounded and checked as they are read
([engine-process.md](engine-process.md)); an unreadable reply ends the engine, which `poll` reports with the
reason. Completed Memory is the `complete` reply's payload, opaque bytes. Input
uses the existing explicit-data session-save encoding; IPC executes no serialized
Python objects. These bounds limit work per call, not elapsed response time.

[designed] Full time is a presentation event, not completion. Publication waits
for the engine's `complete` [designed: T160], an exactly matching complete live
transcript and T64's complete-result, input, Memory/RNG and tail checks; a reply after `complete` (the engine's
end included) before the publication fails the match. `outcome` becomes available
only after successful publication. Repeated reads/actions after consumption fail;
reads never start matches. A second bridge on the same owner or second in-flight
start is refused. The owning caller should pass the token returned by `start` to
every poll/cancel action.

[designed] Active state/template replacement or mutation invalidates the job.
Failures preserve the active state and both seeds. A failed job consumes its token
and permits a fresh start. Cancellation requires the current active token, so a
stale action cannot cancel a newer job. [designed: T160] Cancel asks the engine to end the match and waits up to
`CANCEL_WAIT` (1 s) for its `cancelled`; an engine that does not answer is killed (only the owned process), and the
next start gets a new one. A cancel while the game is still being encoded waits 0.5 s twice, then raises
`TimeoutExpired` and keeps the job owned (#254; `cancel_and_reap` retries); an engine that does not take the game
within the first 0.5 s is killed, which ends the write. Nothing the bridge sends or keeps is a saved game
publication.

[designed] The caller receives actionable errors for guest refusal/no-progress, the engine's exit (its code and
the tail of its stderr, or why its reply could not be read), malformed/truncated IPC and stale
ownership. [designed: T152, #496; T160] The engine runs under PyPy 3.11 (`engine_python()`); a missing PyPy fails
the start with its reason. Play needs no Unicorn (T160 removed the guards that asked for it).
Diagnostic seed/delay/draw-recording options are explicit `start` keyword arguments.
Without `bench=True` a match exposes no in-play controls.

[designed: T102] `start(..., bench=True)` gives the job to a watching player. [designed: T160] The parent's
answers, Enters and acknowledgements are the pipe's `answer`, `pause` and `ack` requests
([engine-process.md](engine-process.md)). At a `half_time`, `pause` or `substitution`
decision the engine sends the event (and `decision`) and waits; `waiting` holds it and `answer(token, pairs)` sends
the (off, on) pairs (none plays on). The engine passes them to `Match.answer` as they are; whether a
pair is legal is the original's. After an answer with pairs the engine sends an `answered` record,
not an event of the match, with what the original `made`, `requested` (at a pause, for the next
stoppage) and `refused` (with the reason; with no substitutions left the original's "no more
substitutes"), and the engine's `substitutions_left`; `reports` collects them. `pause(token)` is
the player's Enter in play (`Match.pause`). With pitch samples, each `ack_frames` is forwarded, and
the engine sends sample k only once sample k − `LEAD` (64) is acknowledged. An engine waiting for an
answer or an acknowledgement is cancelled like any other (#254). `extra_time` and `shootout_order`
keep their default answers; without `bench`, and for `run_watched_match`, every decision plays on.
[designed: T167, #541] `start(..., prompts=True)` (with `bench`) also waits on the player prompts
(`watched_match.PROMPT_CONTEXTS`: `set_piece`, `shootout_order`, `extra_time`): `waiting` holds them as it holds a
bench decision, `choose(token, {'taker': word or None})` or `choose(token, {'shootout_order': [words]})` answers a
prompt, and `answer(token, ())` the menu before extra time. The new window's match day uses it
([ui.md](ui.md)); `CompetitiveJobs.start` passes it on.
Acceptance: `python3 -m unittest goal2.tests.test_watched_bench_t102 -v`.

[designed: T176] A qualifier is watched on the competitive bridge: `CompetitiveJobs.start(frames=True, bench=True)`
plays the pending qualifier as the `competitive` match with the pitch samples and the bench, with the API above, and
its `CompetitivePublication` publishes it, once; the friendly publication is never used for it.
`goal2.desktop.watched.WatchedController` starts a qualifier there (the owner's bridge, the window's, when it has one)
and a friendly on `WatchedJobs`. The budget is the engine's for a competitive match, five a side (BM-7).
Acceptance: `python3 -m unittest goal2.tests.test_watch_qualifiers_t176 -v`.

[designed] Acceptance is `python3 -m unittest goal2.tests.test_watched_jobs -v`.
The suite compares real seeds 257 and 70 for countries7/19, fixture21/year0,
captain0, no requested substitutions, delay0 and draw recording enabled. It checks
the complete synchronous result, ordered events, Memory and both seeds, and prints
measured match time without a hardware-dependent performance assertion. [designed: T160] The window's one
engine process for both kinds of match: `python3 -m unittest goal2.tests.test_matches_on_pipe_t160 -v`. Retained
attempts and controls are under task evidence (`evidence/T65/`, removed 2026-10-20; on branch `local`).
