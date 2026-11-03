# The engine process and its pipe protocol

[designed: owner, 2026-11-03, #527 D3; T159] The window plays its matches in one long-lived engine process, started
under `engine_python()` (PyPy 3.11, `goal2/game/engine_python.py`), and talks to it over that process's stdin and
stdout. The choice and its measurements are in
[design/technology-2026-11/README.md](design/technology-2026-11/README.md) §3.3–3.4 (`measurements/T158/engine-*.json`);
the bugs of the file journals it replaces are in §3.2.

| Side | Module |
| --- | --- |
| The engine (child) | `goal2/game/engine_server.py`, run as `python -m goal2.game.engine_server` |
| The window (parent) | `goal2/game/engine_process.py`, `EngineProcess` |
| The window's matches (T160) | `goal2/game/watched_jobs.py`, `MatchEngine`, under `WatchedJobs` and `CompetitiveJobs` |
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
| `match` | `kind` (`watched` or `competitive`), `fixture`, `options` (`reference_seed`, `delay_byte`, `record_draws`), `frames`, `bench`, `prompts` (optional) | Plays one match. With `prompts` (which needs `bench`) the player prompts are asked too (below). |
| `ack` | `sample` | The window has shown this pitch sample. |
| `pause` | | The player's Enter in play. |
| `answer` | `decision`, and `substitutions` ((off, on) pairs), or `taker` (a player word or null), or `shootout_order` (player words) | Answers the bench decision or player prompt of that number. |
| `cancel` | | Ends the running match. |
| `quit` | | Ends the process. |

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
| `cancelled` | |
| `error` | its text; the process stays up for the next request |

The window adds one of its own: `death` {`code`, `stderr`, `error`} (below).

## The match

The engine plays a match exactly as the two file workers do, never with a driver of its own: `prepare_watched`, or
`prepare_competitive` with `substitutions=(5, 5)` (`goal2/game/watched_worker.py`,
`goal2/desktop/competitive_worker.py`), then `_drive_match` with the pitch samples when `frames` is set. With `bench`
(which needs `frames`) the workers' own `BenchPolicy` answers the decisions, places the Enter and paces the samples:
sample k is sent only once sample k − LEAD has been acknowledged (`watched_jobs.LEAD`). The pipe only replaces the
command journal it reads.

[designed: T167, #541] With `prompts` the match is played with the kit's set-piece prompt (`Match(set_piece=True)`)
and the window also answers `watched_match.PROMPT_CONTEXTS`: the set-piece taker (`set_piece`, answered with `taker`;
null is no key, the original's current pick stands after its wait, F030), the shoot-out order (`shootout_order`) and
the menu before extra time (`extra_time`, answered with no substitutions). Each is announced with `decision` as a
bench decision is, numbered in the same sequence, and passed to `Match.answer` as it is. A match whose takers all
get no key plays as one without the prompts (the same memory and seeds; T167's test).

Commands arrive on a reader thread of the engine and wait in a queue. The match reads them where the workers read
their journal (each paced sample and each decision wait) and, so that a match without the bench can be cancelled too,
also before each event and sample. A `cancel` read there ends the match with `cancelled`, and the process waits for
the next match; commands left over from a match that has ended are ignored.

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

[designed: T160] The window's watched and competitive matches play here, through the bridge API they had on the
file journals ([watched-jobs.md](watched-jobs.md)): `WatchedJobs` (the watched Play, under
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
