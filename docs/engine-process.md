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
| `assistant` | positive integer `request`, `input_hash`, optional `extra_places`2/4 (0omitted); binary JSON state/2 payload | Computes a copied original20candidate and, when requested, balanced additional outfield choices; never edits the retained season or cached legacy game. |
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

[designed: owner#777/T232; confirmed: original1771:377E/3216, DS:0D5C]
`EngineProcess.assistant(state, extra_places=2|4)` keeps the same request,
hash/lifetime/cancellation and process ownership. The original recommended
twenty is snapshotted first. Additional original strength calls run in private
scratch execution; their memory/register effects never replace that snapshot.
Requested replies add `extra_squad`, exactly2/4nullable made-pool words chosen
by the designed balanced-extra policy. Keepers/unavailable players are excluded.
Unrequested, malformed, duplicate or foreign additional IDs fail closed. The
candidate adapter also validates capacity/current membership and outfield
availability before atomic owner publication. Default0omits both the request
field and reply addition, preserving the previous20wire/result shape. Filling
extra places is reported explicitly. This adds no size selector or unsupported
larger-bench activation; all22/24match-day eligibility remains its required
native-engine/UI integration.

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

[designed: T183e/#773; confirmed: T183a/F031 and native finals proof#771]
The in-process owner API `SeasonSession.select_twenty()` explicitly applies the
accepted copied assistant to actual native session state at a ready/complete
manager boundary. It returns detached `selection` metadata and an `observation`;
read `session.state` for the authoritative retained state. An allowed, validated
candidate is retained once; refusal/error leaves that state unchanged. Refusals
report no committed change/recruits and expose no private candidate bytes.
Round call/input identity, persistent keys and fixture/news delivery cursors
stay intact. A held Match/continuation or deferred terminal boundary refuses
before entering the assistant. This synchronous owner operation adds no pipe
action: cancellable worker delivery and the responsive UI remain separately
required before native-season activation. The existing A/Ins opening-career
query and its cancellation/publication guards keep their current behavior.

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
| `stopped_preview` | positive integer `decision` | T170ae: detached current state and exact waiting data at an in-match decision, on the same configured Match. No answer, observation or deltas. |
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

[designed: T170ae/#818] `stopped_preview` returns current `state`, exact waiting
`data`, and `preview={schema:"goal2/stopped-preview/1", decision, managed_country,
state_hash, data_hash}`. Both hashes use canonical JSON. It accepts only current
numbered pause, half-time, extra-time, substitution/opportunity, set-piece or
shoot-out-order decisions; missing, stale, consumed and pre-match requests are
pure repairable refusals. The existing binary JSON payload carries state/2;
the parent verifies the envelope and native consistency before delivering it.
`StoppedMatchSnapshot.from_packet` additionally binds the caller's expected
request, decision, managed country and exact waiting data. Its immutable bytes
yield detached state/data copies, preserving native flags, budgets and prompt
domains. It never publishes a campaign or grants edit permission. The caller
owns lease identity. Driver coordination and current card/menu activation remain
under #817; do not read the driver's reply queue from another consumer.

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

[designed: T170x/#768; confirmed: accepted state/2, T170s/T170w]
`PrematchView.from_preview` is the Qt-free window data boundary. It pairs the
pending pre-match decision with its numbered/hash-verified preview, verifies
current records, context and native squad/pool order, then retains immutable
records and marking words. `display_state()` gives existing card/TEAM decoders
a detached current view, with optional identity overlays and no campaign.
It supplies no backend reference, mutation API, publication or native career
bootstrap. Pool permission is not inferred from legacy campaign metadata.
Native bootstrap and the later match/session lifecycle remain separate.

[designed: T170y/#770] `PrematchController` coordinates confirmed edit/captain
transactions once the process owner has configured the held Match and obtained
its first decision/preview. Its sender is that owner's existing `season_request`;
replies must be marshalled to the controller's owner thread. It sends one answer,
and its process owner must reserve this session exclusively until handoff/detach;
no other client may advance or answer that same session while attached. It then
waits for the fresh pre-match decision and verifies the preview before replacing
the accepted view. It never optimistically patches records. Pure answer refusals
retain the view/decision; malformed/lost replies invalidate without replay.
Play distinguishes omitted captain, null/native default and an exact word.
The first bounded next reply is retained intact in `handoff`; its events are
excluded from `take_events` to give the next driver one delivery path. A native
Play refusal instead returns to a verified pre-match view. `detach` only severs
presentation updates; the existing process/session owner must handle its lease,
discard and close. This coordinator adds no bootstrap, pacing, resume, save or
widget binding.

[designed: T170z/#776] `goal2.ui.held_prematch.HeldPrematchFlow` binds the
existing S15/S08/S09/S10/S16 widgets to an explicitly supplied ready controller,
fixture and reply queue. The native session owner must already hold the exclusive
lease, configure the Match and attach its verified current preview. All replies
are consumed on the Qt owner thread. The facade reads confirmed current records;
identity edits remain the existing word-keyed local overlay. Personal marking
includes eligible outfield bench players and excludes keepers/unavailable/pool.
Pending edits block further backend mutations while local navigation/help remain
usable. Captain Enter sends a current XI word; C/timeout sends explicit null.
Mandatory owner callbacks provide current-route tournament/statistics views,
first-packet handoff and disposal. Handoff receives the intact first next packet
once plus watch/replay preferences; prior edit events remain available through
`controller.take_events()`. Close detaches and calls disposal once, except after
handoff, when the continuing driver owns the session. The adapter never constructs
another Match, confirms a legacy career, resumes/publishes a round or bootstraps
a native career. The normal desktop entry and default route remain separate.
Held A/Ins explains the existing T183 exception; outside-held assistant behavior
is unchanged.

[designed: T170aa/#783] `goal2.game.native_season.NativeSeasonOwner(owner,state)`
is the concrete shared-process owner for an **explicit native state/2**. It checks
the accepted tables and single managed country, retains a detached input/hash,
joins the owner's existing `MatchEngine`, and claims its lease for the entire
session. It does not generate a fresh native career, convert a legacy GameState,
authenticate caller provenance, or repurpose the assistant-only projection.
`poll()` handles open replies on the owner thread; `advance()` is explicit.
`take_observations()` delivers copied native boundary/state packets once, retaining
fixture/news order and duplicates. These packets do not publish a legacy career.
Completed and deferred-terminal boundaries remain explicit.

At a real held Match, `NativeFixture` reads cursor/record/sides/kind and native
stage/year from its route state (Image F023/F024/F030, route87d92501). The owner
configures once with native captain/substitution defaults, consumes no decision
implicitly, and verifies the first pre-match preview before exposing `controller`,
`fixture` and `replies` to `HeldPrematchFlow`. The screen then owns queue delivery;
the season owner's poll stops consuming it. `take_entry_events()` exposes the
entry prefix once. `handoff()` transfers the first Play packet and queue/send
connection once, retaining the shared lease. Later in-match/resume/publication,
native route-view UI, save/load and normal desktop entry remain separate.

`close()` detaches presentation and retires asynchronously without needing a
surviving window/event loop. Its cleanup thread keeps Python alive until owned
process retirement completes, including after the last window exits. It waits for outstanding work, sends discard when
possible, and releases the lease only after its **delivered** discard acknowledgement
or death. At the existing cancellation deadline it kills only its owned process;
no implicit reopen or replay occurs. The EngineProcess object remains usable by
other bridges. Native entry invalidates the shared legacy-game cache to match
the pipe client's policy; a later ordinary match reopens its legacy state on
that same process. Its readonly `generation` counts successful process creations so a
failed launch is distinguishable from the parser/exit-delivery interval. Shared
bridge join/last-leave synchronization prevents a new client inheriting a retiring
engine. After handoff the continuing driver must eventually close this same owner;
closing just the old pre-match presentation does not dispose the running session.

[designed: T170ab/#808; confirmed: T127/T81, match87d92501]
`season.configure(frames=True)` opts the same held Match into completed-tick
samples before execution. `NativeSeasonOwner(...,frames=True)` forwards that
declaration; omitted/False keeps the old configuration arguments and wire shape.
The accepted sampler reads signed poses/ball, officials and holder at each tick
stop, before the generator resumes. No Match is rebuilt or changed privately.

In this opt-in mode each `next` reply contains `frames` (the existing version2
pitch schema) and cumulative canonical `event_count`. Its `events` retain every
non-tick event; tick stops become samples, as in `consume_match`. A frame's
watermark is the number of preceding canonical events over this Match, including
entry/pre-match decisions. `count` still bounds1..32 **raw** stops, including both
ticks and canonical events, and any decision ends its batch. Thus a reply may
contain frames without events, or events without frames. Nothing is coalesced or
dropped; the pull protocol and one pending request provide bounded backpressure.

Parent validation checks frame schema/identity/sequence, signed coordinates,
watermarks within the packet's event interval, exact cumulative count, raw-stop
budget and decision/boolean shape before delivery. Existing frame limits remain.
Counters reset on acknowledged configuration and match/session lifecycle changes;
malformed replies end the session instead of resynchronizing or replaying it.
State/preview/news framing and once-only boundary deltas stay separate. Native
entry refuses early pitch samples; the first Play packet transfers intact through
the existing handoff. This enables the following match-driver/pacing consumer;
pause/replay, native save/publication and normal desktop/default entry are not
implemented by this feed.

[designed: T170ac/#810] `NativeMatchDriver(native_owner)` consumes the owner's
first-packet handoff once (an already obtained connection may be supplied).
Sampling must have been enabled before entry. It retains the absolute native
event count and frame watermarks; `event_base` identifies the already delivered
entry/pre-match prefix. `events` is this driver's suffix and `frames` retains its
received samples, unchanged. `tick(now)` is an owner-thread, nonblocking bounded
poll: it returns a due sample at one of the existing six rates. Only
`painted(sequence)` acknowledges that delivered sample; watched execution stays
within one unhandled sample. `set_held(True)` stops local pulling/presentation.
`quick_result()` handles samples without painting/pacing, preserves their trace,
and still exposes every decision instead of silently selecting answers.

`waiting` appears only after earlier samples are handled. `answer(dict)` sends
its exact numbered SDK answer once, including stopped edit-only tactics/player
changes and explicit taker/order/opportunity answers. `request_pause()` queues
one public Match.pause request until pending work and paint are settled; duplicate
requests are suppressed. The worker's new `pause` action consumes no event:
`paused=true` means Enter was queued, while `paused=false,reason` reports the
SDK's pure guard (over/waiting/shoot-out are not invented menu contexts). The
actual returned decision remains authoritative. Invalid packets/loss dispose the
same owner without replay or publication.

Only actual `over` + `exhausted` and drained samples permit explicit `resume()`.
The driver passes the correlated reply to `NativeSeasonOwner.adopt_resume`:
call/input identity stays unchanged, output hash/RNG/native fixture data are
verified before adoption, and `take_observations()` is the sole delta delivery
path. Complete/terminal boundaries remain explicit; another held Match is
configured/prepared by the same owner. Handoff capabilities are generation-bound,
so an old driver cannot send into a later Match. Once resumed the driver stops
consuming the queue; its presentation can close without discarding the continuing
season. Before resume, `close()` uses the existing asynchronous native disposal.

This is the native driver/resume API, not the full S17/match-day/menu/replay/save
consumer or fresh-native/default entry. `match_day.py` and the other session's
PR796 taker/help fix are unchanged; any following UI binding must retain the fix.

[designed: T170ad/#814] `NativePitchScreen` reuses S17 and PitchWidget over
`NativePitchController` and the retained driver. Construct it inside the held
flow's `on_handoff`, before closing/detaching that flow: its verified current
pre-match view supplies initial roles, sides and kits. No current roster/card
data is taken from the stale route boundary. The screen does not start a Match.
An already consumed `SeasonHandoff` can be supplied explicitly as `connection`.

All four callbacks are required before handoff consumption: `on_decision(screen,
waiting)` receives the native decision number/event; `on_goal(screen,event)`
receives a painted goal with presentation held; `on_complete(screen)` receives
actual drained completion; `on_failure(screen,message)` receives loss or a
callback failure after closing the same owner. Decisions/goals/completion are
delivered once, deferred under help/covered screens. Use explicit
`answer_native(number,answer)`, `release_goal()` and `resume_native()`; quick
presentation never selects an answer. After successful resume the timer and
reply consumption stop. The continuing owner must transfer or close its native
session. Closing before resume uses native asynchronous disposal.

S17 keeps marks, six speeds, reading pause, quick presentation, F9's existing
sound explanation, public bench pause, commentary and paint acknowledgement.
Native canonical watermarks include the earlier pre-match event prefix and
are retained without renumbering; the driver validates their causal bounds.
The Display instance supplies rendering identity and commentary, with no
second playback queue. Full stopped S15/S16/S19 cards/menus need a separate
current in-match read boundary; replay/save prompts belong to the supplied
goal consumer. This explicit consumer is not a normal desktop/default entry.
The adapter advances a detached `events_since(cursor)` suffix and reads the
driver's `shown_count`; idle Qt polls never recopy the full native history.
Hold synchronization changes the driver only on a hold transition, preserving
its six-rate deadline between ordinary polls. The stopped-menu follow-up is #817.

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
