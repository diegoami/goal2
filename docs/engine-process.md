# The engine process and its pipe protocol

[designed: owner, 2026-11-03, #527 D3; T159] The window plays its matches in one long-lived engine process, started
under `engine_python()` (PyPy 3.11, `goal2/game/engine_python.py`), and talks to it over that process's stdin and
stdout. The choice and its measurements are in
[design/technology-2026-11/README.md](design/technology-2026-11/README.md) §3.3–3.4 (`measurements/T158/engine-*.json`);
the bugs of the file journals it replaced are in §3.2. [designed: T161] No match runs over file journals: the
watched and competitive workers and their journals were deleted.

[designed: owner, §6 item 17; T161] One file channel is left, and it is not the engine's: today's window plays its
quick friendly on the Python stand-in in a worker of its own (B2: `goal2/desktop/jobs.py`, `goal2/desktop/worker.py`).
It belongs to today's window and goes with it (T170).

| Side | Module |
| --- | --- |
| The engine (child) | `goal2/game/engine_server.py`, run as `python -m goal2.game.engine_server` |
| The window (parent) | `goal2/game/engine_process.py`, `EngineProcess` |
| The window's matches (T160) | `goal2/game/watched_jobs.py`, `MatchEngine`, under `WatchedJobs` and `CompetitiveJobs` |
| The explicit squad assistant (T183c) | `goal2/game/best_twenty_jobs.py`, on the same owner's `MatchEngine` |
| Tests | `goal2/tests/test_engine_pipe_t159.py`, `goal2/tests/test_matches_on_pipe_t160.py` |

## Packets

Both directions carry the same packets: a 4-byte big-endian length, that many bytes of UTF-8 JSON (an object, the
header), then, when the header has `size`, that many bytes of binary payload. Values keep their tuples as
`goal2.game.session_save` encodes them. A header is at most 16 MiB and a payload at most 64 MiB (`MAX_HEADER`,
`MAX_PAYLOAD`); a packet over either is refused from its declared size before it is read, and a stream that ends
inside a packet is refused as truncated (`ProtocolError`). Both ends use binary streams with no newline translation.

Only the protocol writes to the engine's stdout: at start the engine moves file descriptor 1 to a private one and
points fd 1 and `sys.stdout` at stderr, so a stray print or warning becomes a diagnostic. The window drains stderr on
its own thread and keeps its tail (`EngineProcess.stderr`).

## Requests (window to engine), by `op`

| Request | Fields | What it does |
| --- | --- | --- |
| `open` | payload: the game, `session_save.encode` | Keeps the game; each match plays a fresh copy of it. Sent once per game, not per match. |
| `match` | `kind` (`watched` or `competitive`), `fixture`, `options` (`reference_seed`, `delay_byte`, `record_draws`), `frames`, `bench`, `prompts`, `live_players`, `substitution_control` (optional strict booleans; False omitted) | Plays one match. With `prompts` (which needs `bench`) the player prompts are asked too (below). |
| `ack` | `sample` | The window has shown this pitch sample. |
| `pause` | | The player's Enter in play. |
| `answer` | `decision`, and `substitutions` ((off, on) pairs) with optional `changes` (`positions`, `marking`, `own_tactics`, `tactics`, `edit_only`, T180; request/opportunity below), or `taker` (a player word or null), or `shootout_order` (player words) | Answers the bench decision or player prompt of that number. |
| `cancel` | | Ends the running match. |
| `quit` | | Ends the process. |
| `season` | `request` (positive integer), `action`, fields below | Operates on one retained sealed season; separate from the legacy fresh-match requests. |
| `assistant` | positive integer `request`, `input_hash`; binary JSON state/2 payload | Computes a copied private best-twenty candidate; never edits the retained season or cached legacy game. |
| `assistant_cancel` | positive integer `request` | Cancels only that query; late controls cannot cancel another operation. |

## Replies (engine to window), by `kind`, with `value`

| Reply | Value |
| --- | --- |
| `ready` | `implementation`, `version`, `pid`: sent once at start |
| `opened` | |
| `event` | a match event (`Event`) |
| `frame` | a pitch sample (`goal2/game/watched_pitch.py`) |
| `decision` | `decision` (its number, from 0), `event`: the bench waits for its `answer` |
| `answered` | what the engine made of an answer (`watched_match._report`) |
| `pause_dropped` | the sample after which the original could not take the Enter (#316) |
| `complete` | the outcome's `result`, `events`, `seeds`, `engine_year`; the payload is its memory |
| `settled` | no value or payload; closes the preceding completion transaction |
| `cancelled` | |
| `error` | its text; the process stays up for the next request |
| `season` | `request`, `action`, and the detached operation result described below |
| `season_error` | `request`, `error`, `lost` (whether the transient season was invalidated) |
| `assistant` | `request`, `input_hash`, `output_hash`, `result`; binary JSON state/2 payload |
| `assistant_error` | `request`, `error`; no payload |
| `assistant_cancelled` | `request`; no payload |

The window adds one of its own: `death` {`code`, `stderr`, `error`} (below).

## Explicit assistant (T183c)

[designed: owner fast-track, T183c] `EngineProcess.assistant(state)` returns a request
number immediately; its terminal reply is bound to that request and canonical input/output
hashes. Result metadata contains strict allowed/refusal flags, country/manager, ordered squad
and pool, recruits and original call evidence. The client validates packet/schema/hash/type
bounds. A mismatched reply ends the child; a rejected copied context leaves it reusable.
Busy, close and death include the assistant request. Cancellation is request-specific,
including results already in transit; its deadline cannot kill a later operation/process.

`AssistantJobs` joins the existing `MatchEngine`; it starts no sidecar. It snapshots current
state on its owner thread, prepares/executes/builds the private candidate off that thread,
and only owner-thread `poll` validates and installs it. Cancellation remains accepted through
validation until the atomic commit; state identity/value are rechecked at that boundary.
Refusal/cancel/stale/failure install nothing. Leaving the view cancels its request; closing or
replacing the career closes its bridge without leaking replies into the next match.

[derived: T183b] The current legacy window projects its supported opening phase (2/5),
including its actual world prefix and current XI/pool, into transient assistant input. It
preserves immutable tables and opaque fields. This is not a whole native calendar/bootstrap
or later-stage migration; T183's full native later-season/finals acceptance remains required.
The engine operation itself accepts genuine outside-match state/2 and runs the original
preparation and DC7E under PyPy without Unicorn or a GOAL.EXE read.

## Retained season (T170o)

[designed: T170o/#735] `EngineProcess.season_open(state, keys=None)` explicitly opens
accepted state/2 in the same PyPy process. It sends `action=open`, with a binary
UTF-8 JSON payload containing `state` and `keys`. The worker owns one `SeasonSession`,
its persistent Keys, continuation, and actual pending Match. The legacy `open`/`match`
requests require the season to have been discarded first. One season request may
be outstanding at a time; its numbered reply ends that request.

`season_request(action, **fields)` accepts these operations:

| Action | Fields | Result |
| --- | --- | --- |
| `advance` | | One original route call; refuses while a Match is held. |
| `observe` | | Detached current boundary, with empty deltas. |
| `preview` | positive integer `decision` | T170s: detached current pre-match state; only while that configured decision waits. No observation or deltas. |
| `configure` | optional `captain`, `substitutions` | Configures the actual pending Match exactly once through `PrematchSeam`. |
| `next` | optional `count`, integer 1..32 (default 32) | At most that many `events` as plain Event records, stopping at every decision; returns `decision` (number or null), `over`, `exhausted`. |
| `answer` | `decision`, `answer` (Match.answer keyword object) | Answers that still-waiting numbered decision once. JSON element-map keys become integers. T170p adds `captain` on pre-match Play after edits. |
| `resume` | | Resumes the same completed Match after all its events have been drained. |
| `discard` | | Drops the transient session and Match; never publishes them. |

[confirmed: vendored match.py, Match.events] Taking another event at an unanswered
decision otherwise plays on by default. The worker refuses `next` until an explicit
numbered answer arrives. The answer's legal context and player membership remain
the kit's decisions. This bounded event interface introduces no pitch pacing or
window controls; those follow in the activation leaves.

[designed: T170o] `open`, `advance`, `observe`, and `resume` return `observation`
(the detached SeasonObservation fields); the binary UTF-8 JSON payload is the
detached state/2. The parent verifies its canonical hash against `output_hash` and
adds `state` to the callback value. Advance/resume deliver their own fixture/news
deltas exactly once. A held Match is still an incomplete round, never a publishable
candidate. Event/answer requests retain private Match memory in the child.

[designed: T170t/#751; confirmed: archaeology `fb6d3093`, F039/news]
News snapshots keep every original cell byte and provenance field. On the wire,
each raw page's `cells` uses `{schema:"goal2/news-cells/1", base64:<text>}`.
The season-only adapter validates the exact snapshot fields, 4000 decoded bytes,
provenance types and word tuples. After generic tuple restoration, the parent
restores `cells` to bytes, preserving the worker's detached dictionary/tuple
shape and ordered duplicate pages. Malformed snapshots are protocol failures;
the existing state/observation hash check still applies. Empty observe deltas
stay empty. The generic save encoder still rejects raw bytes: this is transient
season transport, with no save-schema change. Public receipts contain hashes
and counts, never actual original cells.

[designed: T170s/#746; confirmed: T170r audit at archaeology `fb6d3093`]
`preview` returns `preview={schema:"goal2/prematch-preview/1", decision, state_hash}`
and the current state/2 in the binary JSON payload. The parent checks that identity,
requested decision, state schema and canonical hash before adding `state` to the
callback value. Both teams, pool and current player records come from the same
held Match's public `records_after()` read. Repeated reads do not consume events,
answer a decision or modify the route-boundary state. A stale/consumed decision,
missing configuration or a different phase refuses purely. Preview is separate
from `SeasonObservation`: it is neither a completed-round candidate nor a save or
active-session serialization. A subsequent edit requires a fresh numbered
decision/preview; only completed Match resume can publish the round. Existing
one-outstanding-request and explicit recovery rules apply.

A known pure request refusal replies `season_error` with `lost=false`; an engine or
decode failure invalidates the season (`lost=true`). Worker death clears the
parent's season holding; subsequent requests refuse until an explicit `season_open`.
State/2 is never cached for automatic replay, nor is a pending Match serialized.
`close()` retains its bounded quit/kill behavior. Later leaves wire the window,
in-match pacing, round publication and save/load policy over these primitives.

[confirmed: archaeology T135 at `fc6b5294`, F010/F031; designed: T170u/#753]
At configured pre-match decisions, `answer` accepts edit-only `positions` mapping
current squad/pool words to integer0..13 or explicit `"club"`. Numeric goals use
the original R path; club presses C once, including already-equal values. The
held seam exposes `set_position(player, code)` and `club_position(player)`;
numeric booleans are refused rather than coerced. The4952 entry/E72A return
witness and actual guest ordering come from the accepted kit. Known-pure
pre-match position validation errors reply `lost=false` and retain the same
repairable decision. Driver/backend failures still invalidate the session.
After a successful edit, consume its fresh decision and request a current preview;
the season's route boundary stays unchanged. Play remains a separate answer.
[confirmed: T170v, archaeology T136/46315dcf] Pre-match `own_tactics`
maps current squad or made-pool words to elements1..4 with exact JSON false,
true or null (inherit). `PrematchSeam.set_own_tactic` preserves all three values.
Inheritance uses the player's country default, including pool players. Edit-only
requests run the original T menu on the held Match; Play remains separate. Pure
invalid own inputs retain the decision and current preview for repair; genuine
backend failures still lose the session.

[confirmed: T137/87d92501; designed: T170w/#763] Pre-match edit-only `marking`
maps eligible squad words, including available outfield bench players, to exact
null (inherit), integer0 (explicit protected zone) or an available opponent word
in original slots2..11. `PrematchSeam.set_marking` preserves these values.
Inheritance is status element7 clear; protected zone is element7 set and word0.
Read both from the current preview, whose state/2 retains the native marking
table; a zero target word alone cannot identify inheritance. Whole-packet
projected membership/role validation is pure. Invalid marking replies retain the
same decision with `lost=false`; genuine driver/backend faults invalidate.
Successful edits yield a fresh decision/preview; Play remains separate.
The complete window flow still requires activation.

[designed: T170p; confirmed: archaeology T133/#715] After accepted pre-match
edits, `answer={"captain": word}` plays with a current eligible XI member, including
a pool player just brought in. `captain: null` uses the original default; omission
keeps initial configuration. A rejected captain answer consumes no decision,
memory, RNG or replay action, so its named `season_error` has `lost=false` and
the same decision can be repaired. `PrematchSeam.play(captain=...)` preserves the
same distinction. The original role-1 prompt receives the choice through keys.

[designed: T170q; confirmed: archaeology T134/#717, F031/F012/F010] A pre-match
edit-only `substitutions` pair may use any current squad outgoing word and a
different squad or made-pool incoming word. Starter/starter reorder and bench/
pool exchange follow DEA6's real word swap and original XI/bench sorts; callers
use the fresh decision order. These pre-match edits spend no substitution budget
or match tick. Bad pair validation is pure, reports its named `season_error`
with `lost=false`, and keeps the same decision for repair. Runtime/plan failures
still invalidate the private session. Ordinary in-match substitution rules stay
unchanged. This adds no window controls or automatic model publication.

## The match

The engine plays a match with the shared driver, never with one of its own: `prepare_watched`, or
`prepare_competitive` with `substitutions=(5, 5)`, then `_drive_match` with the pitch samples when `frames` is set.
With `bench` (which needs `frames`) `BenchPolicy` (`engine_server.py`) answers the decisions, places the Enter and
paces the samples: sample k is sent only once sample k − LEAD has been acknowledged (`watched_jobs.LEAD`).
[designed: T161] These are the deleted file workers' preparation, driver and `BenchPolicy`, unchanged but for the
channel they read.

[designed: T167, #541] With `prompts` the match is played with the kit's set-piece prompt (`Match(set_piece=True)`)
and the window also answers `watched_match.PROMPT_CONTEXTS`: the set-piece taker (`set_piece`, answered with `taker`;
null is no key, the original's current pick stands after its wait, F030), the shoot-out order (`shootout_order`) and
the menu before extra time (`extra_time`, answered with no substitutions). Each is announced with `decision` as a
bench decision is, numbered in the same sequence, and passed to `Match.answer` as it is. A match whose takers all
get no key plays as one without the prompts (the same memory and seeds; T167's test).

[designed: owner #636] `substitution_control=True` requires the interactive bench and pitch samples.
Every opted-in decision carries the authoritative boolean `request_substitution`; `live_players=True`
independently requires the complete current player-record snapshot. The match day explicitly uses both.
An ordinary pause accepts `changes={"request_substitution": true|false, "edit_only": true}` with no
player pair. False is an explicit cancellation, never an empty change. The fresh stopped decision
acknowledges the actual latch, including a refusal, without spending allowance or continuing Play.

A distinct `substitution_opportunity` decision carries `keeper_unavailable`, `timeout_polls` (400 ordinary,
1000 unavailable keeper), and `poll_ms` (10 nominal); it takes only
`changes={"opportunity": "accept"|"dismiss"|"timeout"}`. It is not a legal pair-selection decision.
Acceptance drives the original accepting key, then waits for the guest's real `substitution` decision
before enabling a pair. Literal original Esc is `dismiss`; no key is `timeout`, including the original's
forced keeper-menu distinction. The UI's Esc accepts as the owner's explicit key mapping. A consumed
notice hides its timer; it does not invent cancellation when the actual request remains set.
Legacy clients omitting these capabilities retain their existing packet/event/answer profiles.

Commands arrive on a reader thread of the engine and wait in a queue. The match reads them at each paced sample and
each decision wait and, so that a match without the bench can be cancelled too, also before each event and sample. A
`cancel` read there ends the match with `cancelled`, and the process waits for the next match; commands left over
from a match that has ended are ignored.

## Lifetimes

- **One process for the window's life.** `EngineProcess` starts it at the first `open` or `match`; one match runs at a
  time, and there are no tokens: one pipe is ordered and private.
- **The engine's death.** End of its stdout, or its exit, is reported once as `death` with its exit code and the tail
  of its stderr (`error` names an unreadable reply, after which the window kills it). The next `open` or `match`
  starts a new process, which is sent the last game before the match.
- **A cancel left unanswered** for `CANCEL_DEADLINE` (10 s) is ended by killing the process: a death.
- **The window's death.** End of the engine's stdin ends the engine wherever it waits, a decision's answer or an
  acknowledgement included (#417).
- **`close()`** sends `quit`, waits up to 2 s, then kills; that end is not reported as a death.

## The window's matches

[designed: T160] The window's watched and competitive matches play here, through the bridge API
([watched-jobs.md](watched-jobs.md)): `WatchedJobs` (the watched Play, under
`goal2/desktop/watched.py`'s `WatchedController`) and `CompetitiveJobs` (`goal2/desktop/competitive.py`; [designed: T176]
also under `WatchedController` for a watched qualifier, `kind: competitive` with `frames` and `bench`). The owner
(the window's model) holds one `MatchEngine`, which both bridges share:

- It owns one `EngineProcess`. The game is sent with `open` once, and again only when the game a match plays (the
  publication's prepared state and the template) differs from the last one sent, or the process is new. The game is
  encoded and sent on a thread; the owner's thread sends the `match`.
- One match is attached at a time. The reader thread's replies go to that match's queue, which the bridge's `poll`
  and `poll_frames` drain on the owner's thread; a cancelled or replaced match is detached before the next starts, so
  its replies never reach the next one. A cancel waits for the engine's `cancelled` up to `CANCEL_WAIT` (1 s), then
  kills the process.
- A `death` is reported through `poll` as the engine's exit (its code, and the error or the tail of its stderr); the
  next match starts a new process.
- The process is closed when the owner's last bridge closes: the window's close (#417).

## Completion confirmation

[designed: T199, #627] `complete` supplies a candidate result; the following private `settled` frame closes that
transaction. The client holds the result until this frame, then exposes the existing single `complete` callback.
Confirmation is not a game event and changes no canonical event, result, RNG or memory. Duplicate completions,
truncated trailers, bad confirmations and process failure before confirmation cannot become publishable.
Cancellation at this boundary discards the candidate. The existing cancellation deadline bounds a worker that
never confirms; a valid confirmation cancels that watchdog. Public busy remains true until confirmation.

A malformed packet after confirmation still ends the worker and cannot complete a second time; an already
committed valid prior game is not rewritten. Synthetic replay workers emit confirmation only after their
deliberate fault injections. Original recorded event/result/memory fixture bytes stay unchanged.
