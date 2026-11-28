"""[designed: owner, 2026-11-03, #527 D3; T159] The window's side of the engine process (goal2.game.engine_server).

`EngineProcess(on_reply)` starts the child once under engine_python() (PyPy 3.11), sends it requests and reads its
replies on a reader thread; each reply goes to `on_reply(kind, value)` on that thread (goal2/game has no Qt: the
window turns the call into a signal). The protocol is docs/engine-process.md's.

- `open(state, template)` sends the game, encoded as a save (goal2.game.session_save), once per game, never per
  match: the engine keeps it and plays each match on a fresh copy.
- `match(kind, fixture, ...)` starts a watched or competitive match; one at a time. `ack`, `pause`, `answer` and
  `cancel` speak to the running match. No tokens: one pipe is ordered and private.
- The child's end (end of its stdout, or its exit) is reported once as `death` {code, stderr, error}, with its exit
  code and the tail of its stderr; the next `open` or `match` starts a new process, which is sent the last game
  before the match.
- A `cancel` the engine has not answered within `cancel_deadline` seconds is ended by killing the process: a death.
- `close()` sends `quit`, waits briefly, then kills; that end is not reported.

Replies and their values: `ready` {implementation, version, pid}; `opened`; `event` (an Event); `frame` (a pitch
sample, goal2.game.watched_pitch); `decision` {decision, event}; `answered` (the engine's report,
watched_match._report); `pause_dropped` (the sample); `complete` (a WatchedOutcome); `cancelled`; `error` (its text).
"""
from __future__ import annotations

import subprocess
import sys
import threading
from dataclasses import asdict
from pathlib import Path

from goal2.game.engine_server import (KINDS, MAX_HEADER, MAX_PAYLOAD, OPTIONS, ProtocolError, encode_packet,
                                      read_packet)

ROOT = Path(__file__).resolve().parents[2]
MODULE = "goal2.game.engine_server"
# [designed: T159] How long a cancel may go unanswered before the process is killed. The engine reads it at every
# event and pitch sample, milliseconds apart in play; the longest stretch without one is a match's preparation.
CANCEL_DEADLINE = 10.0
# [designed: T159] How long close() waits for the engine to leave after `quit`.
QUIT_WAIT = 2.0
STDERR_TAIL = 4096
_MANAGEMENT_REPLIES = ('position', 'position_error', 'roster_move', 'roster_move_error')


class _Life:
    """One child process and what is known of its end."""

    def __init__(self, process):
        self.process = process
        self.quiet = False          # close(): the end is not a death
        self.stderr = bytearray()
        self.drain = None


class EngineProcess:
    def __init__(self, on_reply, *, command=None, cancel_deadline=CANCEL_DEADLINE):
        self.on_reply = on_reply
        self.command = None if command is None else list(command)
        self.cancel_deadline = cancel_deadline
        self._life = None
        self._game = None
        self._lock = threading.RLock()
        self._write = threading.Lock()
        self._match = None           # the running match's number
        self._completion = None      # [designed: T199] private until the reply transaction ends
        self._cancelled_completion = False
        self._completion_timer = None
        self._matches = 0
        self._live_players = False
        self._selected_bench = None
        self._substitution_control = False
        self.opens = 0               # `open` requests sent, over every process
        self.ready = None            # the current process's `ready` value
        self.closed = False
        self._generation = 0
        self._season_active = False
        self._season_request = None
        self._season_requests = 0
        self._reset_season_pitch()
        self._assistant_request = None
        self._assistant_requests = 0
        self._assistant_cancelled = False
        self._management_request = None
        self._management_requests = 0
        self._management_cancel = None

    # --- state ---------------------------------------------------------------------------------------------------

    @property
    def generation(self):
        """[designed: T170aa] Successful process creations, retained across exits."""
        with self._lock:
            return self._generation

    @property
    def process(self):
        life = self._life
        return life.process if life is not None else None

    @property
    def pid(self):
        process = self.process
        return process.pid if process is not None else None

    @property
    def stderr(self) -> str:
        """The tail of the current process's stderr: its diagnostics."""
        life = self._life
        return bytes(life.stderr).decode("utf8", "replace") if life is not None else ""

    @property
    def busy(self) -> bool:
        return (self._match is not None or self._completion is not None
                or self._season_request is not None or self._assistant_request is not None
                or self._management_request is not None)

    def edit_position(self, state, *, revision, player, key):
        """[designed: T170bg] Send one detached standalone R/C candidate request."""
        from goal2.game.native_management_wire import position_check
        from goal2.game.native_position import validate_selection

        validate_selection(player, key)
        return self._request_management('position', state, revision, lambda source: position_check(source, player, key),
                                        player=player, key=key)

    def move_roster(self, state, *, revision, first, second):
        """[designed: T170bj] Ask for one validated standalone move or exchange."""
        from goal2.game.native_management_wire import roster_check
        from goal2.game.native_roster_move import validate_pair

        validate_pair(first, second)
        return self._request_management('roster_move', state, revision, lambda source: roster_check(source, first, second),
                                        players=[first, second])

    def _request_management(self, operation, state, revision, prepare, **fields):
        import json
        from goal2.game.season import canonical_hash

        if type(revision) is not int or revision < 0:
            raise ValueError(f'invalid campaign revision for {operation} request')
        with self._lock:
            self._usable()
            if self.busy:
                raise ValueError('the engine has a pending request')
            if self._season_active:
                raise ValueError('discard the held season before making a standalone edit')
            payload = json.dumps(state, allow_nan=False, separators=(',', ':')).encode('utf8')
            source = json.loads(payload)
            verify = prepare(source)
            number = self._management_requests + 1
            binding = dict(request=number, revision=revision, input_hash=canonical_hash(source), **fields)
            if self._life is None:
                self._start()
            self._send(dict(op=operation, **binding), payload)
            self._management_request = operation, binding, verify
            self._management_requests = number
            return number

    def cancel_position(self, number):
        """Fence this candidate and keep the pipe occupied until the reply or death."""
        return self._cancel_management('position', number)

    def cancel_roster_move(self, number):
        """Fence the move, including a refusal or candidate already in transit."""
        return self._cancel_management('roster_move', number)

    def _cancel_management(self, operation, number):
        with self._lock:
            pending = self._management_request
            if (type(number) is not int or pending is None or pending[0] != operation
                    or number != pending[1]['request']):
                return False
            if self._management_cancel is None:
                timer = threading.Timer(self.cancel_deadline, self._management_overdue, args=(self._life, pending))
                timer.daemon = True
                self._management_cancel = timer
                timer.start()
            return True

    def _management_overdue(self, life, pending):
        with self._lock:
            if self._life is life and self._management_request is pending:
                life.process.kill()

    def _clear_management(self):
        self._management_request = None
        timer, self._management_cancel = self._management_cancel, None
        if timer is not None:
            timer.cancel()

    def _decode_management(self, kind, value, payload):
        import json
        import zlib
        from goal2.game.season import canonical_hash

        pending = self._management_request
        if pending is None:
            raise ProtocolError(f'unexpected {kind} reply')
        operation, binding, verify = pending
        if (kind not in (operation, operation + '_error') or not isinstance(value, dict)
                or type(value.get('request')) is not int or value['request'] != binding['request']):
            raise ProtocolError(f'stale or unexpected {operation} reply')
        if kind.endswith('_error'):
            if payload or set(value) != {'request', 'error'} or not isinstance(value['error'], str):
                raise ProtocolError(f'invalid {operation} error reply')
        else:
            if any(type(value.get(k)) is not type(v) or value[k] != v for k, v in binding.items()):
                raise ProtocolError(f'invalid {operation} result binding')
            if operation == 'roster_move' and any(type(word) is not int for word in value['players']):
                raise ProtocolError('invalid roster_move player words')
            fields = {key: item for key, item in value.items() if key not in binding}
            try:
                output_hash = fields.pop('output_hash')
                state = json.loads(payload.decode('utf8')) if payload else None
                if payload and not isinstance(state, dict):
                    raise ValueError('state payload is not an object')
                if (canonical_hash(state) if payload else None) != output_hash:
                    raise ValueError('output hash differs')
                verify(state, fields)
            except (ValueError, TypeError, KeyError, IndexError, OverflowError, zlib.error) as exc:
                raise ProtocolError(f'invalid {operation} result: {exc}') from exc
            value['state'] = state
        if self._management_cancel is not None:
            kind, value = operation + '_cancelled', {'request': binding['request']}
        self._clear_management()
        return kind, value

    def assistant(self, state, *, extra_places=0):
        """[designed: T183c] Ask on a private state/2; replies are request/hash bound."""
        import json
        from goal2.game.season import canonical_hash
        if type(extra_places) is not int or extra_places not in (0,2):
            raise ValueError('additional assistant places must be0or2')
        if not isinstance(state, dict) or state.get('schema') != 'original_match.state/2':
            raise ValueError('assistant input must be state/2')
        payload = json.dumps(state, allow_nan=False, separators=(',', ':')).encode('utf8')
        digest = canonical_hash(state)
        with self._lock:
            self._usable()
            if self.busy:
                raise ValueError('the engine has a pending request')
            if self._life is None:
                self._start()
            number = self._assistant_requests + 1
            self._assistant_request = (number, digest, extra_places)
            self._assistant_cancelled = False
            try:
                fields={'extra_places':extra_places} if extra_places else {}
                self._send({'op': 'assistant', 'request': number, 'input_hash': digest, **fields}, payload)
            except Exception:
                self._assistant_request = None
                raise
            self._assistant_requests = number
            return number

    def cancel_assistant(self, number):
        """Cancel this query only, including a result already in transit."""
        with self._lock:
            if (type(number) is not int or self._assistant_request is None
                    or number != self._assistant_request[0] or self._life is None):
                return False
            self._assistant_cancelled = True
            self._send({'op': 'assistant_cancel', 'request': number})
            timer = threading.Timer(self.cancel_deadline, self._assistant_overdue,
                                    args=(self._life, number))
            timer.daemon = True
            timer.start()
            return True

    def _assistant_overdue(self, life, number):
        with self._lock:
            if (self._life is life and self._assistant_request is not None
                    and self._assistant_request[0] == number):
                life.process.kill()

    @property
    def season_active(self):
        """[designed: T170o] A transient session exists only in this live child."""
        return self._season_active

    def _reset_season_pitch(self):
        # [designed: T170ab] Match-local presentation counters, never a replay cache.
        self._season_pitch=False;self._season_pitch_pending=False
        self._season_pitch_sequence=0;self._season_pitch_watermark=0;self._season_pitch_events=0
        self._season_pitch_limit=32

    def season_open(self, state, *, keys=None):
        """Explicitly open state/2, never retained for replay after process death."""
        import json
        payload = json.dumps({'state': state, 'keys': keys}, allow_nan=False,
                             separators=(',', ':')).encode('utf8')
        with self._lock:
            self._usable()
            if self.busy:
                raise ValueError('the engine has a pending request')
            if self._life is None:
                self._game = None
                self._start()
            self._season_send('open', payload=payload)

    def season_request(self, action, **values):
        """One asynchronous season operation; replies arrive through on_reply."""
        from goal2.game.season_worker import FIELDS
        if action == 'open' or action not in FIELDS:
            raise ValueError('use season_open for an explicit season open')
        with self._lock:
            self._usable()
            if self.busy:
                raise ValueError('the engine has a pending request')
            if not self._season_active or self._life is None:
                raise ValueError('no live season; explicitly open a state/2')
            self._season_send(action, **values)

    def _season_send(self, action, *, payload=b'', **values):
        from goal2.game.season_worker import validate_request
        number = self._season_requests + 1
        header = dict(op='season', request=number, action=action, **values)
        validate_request(header)
        if action=='configure':self._season_pitch_pending=values.get('frames',False)
        if action=='next':self._season_pitch_limit=values.get('count',32)
        self._send(header, payload)
        self._season_requests = number
        self._season_request = (number, action, values.get('decision'))

    # --- requests ------------------------------------------------------------------------------------------------

    def open(self, state, template) -> None:
        from goal2.game.session_save import encode
        self.open_encoded(encode(state, template))

    def open_encoded(self, raw: bytes) -> None:
        """Send an encoded game (session_save.encode); a new process is started when there is none."""
        with self._lock:
            self._usable()
            if self._season_active:
                raise ValueError('discard the held season before opening a legacy game')
            if self.busy:
                raise ValueError("the engine is playing a match; cancel it before opening another game")
            self._game = bytes(raw)
            if self._life is None:
                self._start()
            else:
                self._send_open()

    def match(self, kind, fixture, *, options=None, frames=False, bench=False, prompts=False,
              live_players=False, substitution_control=False, selected_bench=None) -> None:
        """Start a match on the open game: `kind` watched or competitive; `options` among reference_seed,
        delay_byte and record_draws; `frames` streams the pitch samples; `bench` (with frames) asks the bench's
        decisions and paces the samples on `ack`; `prompts` (with the bench) also asks the player prompts
        (watched_match.PROMPT_CONTEXTS: the set-piece taker, the shoot-out order, the menu before extra time) [designed:
        T167, #541]."""
        options = dict(options or {})
        if (kind not in KINDS or type(frames) is not bool or type(bench) is not bool or type(prompts) is not bool
                or (prompts and not bench) or type(live_players) is not bool
                or type(substitution_control) is not bool or (substitution_control and not (bench and frames))):
            raise ValueError("invalid engine match request")
        if bench and not frames:
            # [designed: #316] the original takes the player's Enter in play at a pitch sample
            raise ValueError("the bench needs the pitch samples (frames=True)")
        if set(options) - set(OPTIONS):
            raise ValueError(f"engine match options are {', '.join(OPTIONS)}")
        selection = None
        if selected_bench is not None:
            from goal2.game.extended_save import from_data, to_data
            selection, slots = from_data(selected_bench)
            if (selection.first, selection.second, selection.index, selection.kind) != (
                    fixture.first, fixture.second, fixture.index, fixture.kind):
                raise ValueError('selected-bench request differs from fixture')
            selected_bench = to_data(selection, slots)
        with self._lock:
            self._usable()
            if self._season_active:
                raise ValueError('discard the held season before playing a legacy match')
            if self.busy:
                raise ValueError("the engine is already playing a match")
            if self._game is None:
                raise ValueError("no game is open")
            if self._life is None:
                self._start()
            self._matches += 1
            self._match = self._matches
            self._live_players = live_players
            self._selected_bench = selection
            self._substitution_control = substitution_control
            self._events = []
            self._frame_sequence, self._frame_watermark = 0, 0
            request = {"op": "match", "kind": kind, "fixture": asdict(fixture), "options": options,
                       "frames": frames, "bench": bench}
            if prompts:
                request["prompts"] = True
            if live_players:
                request["live_players"] = True
            if substitution_control:
                request["substitution_control"] = True
            if selection is not None:
                request["selected_bench"] = selected_bench
            self._send(request)

    def ack(self, sample: int) -> bool:
        """The window has shown pitch sample `sample`: the engine may run LEAD samples past it."""
        if type(sample) is not int or sample < 0:
            raise ValueError("invalid pitch sample acknowledgement")
        return self._command({"op": "ack", "sample": sample})

    def pause(self) -> bool:
        """The player's Enter in play."""
        return self._command({"op": "pause"})

    def answer(self, decision: int, substitutions=(), *, choice=None, changes=None) -> bool:
        """Answer bench decision `decision` with (off, on) pairs; none plays on. `choice` answers a player prompt
        instead: {'taker': word or None} or {'shootout_order': [words]} [designed: T167, #541]. `changes` adds the
        bench's positions, marks and own tactics to the same answer (watched_jobs.CHANGES) [designed: T180]."""
        from goal2.game.watched_jobs import _changes, _choice, _pairs
        if type(decision) is not int or decision < 0:
            raise ValueError("invalid bench decision number")
        if choice is not None:
            return self._command(dict({"op": "answer", "decision": decision}, **_choice(choice)))
        command = {"op": "answer", "decision": decision, "substitutions": _pairs(list(substitutions))}
        changes = _changes(changes or {})
        if changes:
            command["changes"] = changes
        return self._command(command)

    def cancel(self) -> bool:
        """End the running match; the engine replies `cancelled` and stays up. Unanswered within the deadline, the
        process is killed."""
        with self._lock:
            number = self._match
            if self._completion is not None:
                self._cancelled_completion = True
                return True
            elif not self._command({"op": "cancel"}):
                return False
            timer = threading.Timer(self.cancel_deadline, self._overdue, args=(number,))
            timer.daemon = True
            timer.start()
            return True

    def close(self) -> None:
        with self._lock:
            self.closed = True
            if self._completion is not None:
                self._cancelled_completion = True
            life = self._life
            if life is None:
                return
            life.quiet = True
            try:
                self._send({"op": "quit"})
            except OSError:
                pass
        try:
            life.process.wait(timeout=QUIT_WAIT)
        except subprocess.TimeoutExpired:
            life.process.kill()
            life.process.wait()
        self._ended(life)

    # --- internals -----------------------------------------------------------------------------------------------

    def _usable(self):
        if self.closed:
            raise ValueError("the engine process is closed")

    def _command(self, header) -> bool:
        with self._lock:
            if self._match is None:
                return False
            self._send(header)
            return True

    def _send(self, header, payload=b""):
        packet = encode_packet(header, payload)
        with self._write:
            stream = self._life.process.stdin
            stream.write(packet)
            stream.flush()

    def _send_open(self):
        self._send({"op": "open"}, self._game)
        self.opens += 1

    def _start(self):
        from goal2.game.engine_python import worker_command
        command = worker_command(MODULE) if self.command is None else self.command
        # [designed: T159, the task's Windows hazard] binary pipes on every stream; stderr drained on its own thread
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, bufsize=0)
        self._generation += 1
        life = _Life(process)
        life.drain = threading.Thread(target=self._drain, args=(life,), name="goal2-engine-stderr", daemon=True)
        life.drain.start()
        self._life = life
        self.ready = None
        threading.Thread(target=self._read, args=(life,), name="goal2-engine-replies", daemon=True).start()
        if self._game is not None:
            self._send_open()

    def _drain(self, life):
        stream = life.process.stderr
        while True:
            chunk = stream.read(4096)
            if not chunk:
                stream.close()
                return
            life.stderr += chunk
            del life.stderr[:-STDERR_TAIL]

    def _overdue(self, number):
        with self._lock:
            pending = self._completion is not None and self._matches == number
            if (self._match == number or pending) and self._life is not None:
                self._life.process.kill()

    def _read(self, life):
        error = None
        try:
            while True:
                packet = read_packet(life.process.stdout, max_header=MAX_HEADER, max_payload=MAX_PAYLOAD)
                if packet is None:
                    break
                reply = self._decode(life, *packet)
                if reply is not None:
                    self._deliver(*reply)
        except (ProtocolError, ValueError, TypeError, KeyError) as exc:
            # [designed: T159] A reply that cannot be read ends the engine: the stream cannot be resynchronised.
            error = f"{type(exc).__name__}: {exc}"
            life.process.kill()
        except OSError as exc:
            error = f"{type(exc).__name__}: {exc}"
        life.process.wait()
        with self._lock:
            unfinished = self._life is life and self._completion is not None
        if unfinished and error is None:
            error = (f"engine exited ({life.process.returncode}) after its completion" if life.process.returncode
                     else "engine ended before confirming its completion")
        life.process.stdout.close()
        if life.drain is not None:
            life.drain.join(2)
        if self._ended(life) and not life.quiet:
            self._deliver("death", {"code": life.process.returncode,
                                    "stderr": bytes(life.stderr).decode("utf8", "replace"), "error": error})

    def _ended(self, life) -> bool:
        """Forget `life` if it is still the current process; whether it was."""
        with self._lock:
            if self._life is not life:
                return False
            self._life = None
            self._season_active = False
            self._season_request = None
            self._reset_season_pitch()
            self._assistant_request = None
            self._assistant_cancelled = False
            self._clear_management()
            self._match = None
            self._take_completion()
            self.ready = None
        for stream in (life.process.stdin,):
            try:
                stream.close()
            except OSError:
                pass
        return True

    def _decode(self, life, header, payload):
        from goal2.game.session_save import _restore_json_value
        from goal2.game.watched_jobs import _event, _report
        kind = header.get("kind")
        value = _restore_json_value(header.get("value"), "engine reply")
        with self._lock:
            if self._life is not life:
                if kind in ('assistant', 'assistant_error', 'assistant_cancelled', *_MANAGEMENT_REPLIES):
                    return None
                return kind, value
            if kind == "ready":
                if not isinstance(value, dict):
                    raise ProtocolError("invalid ready reply")
                self.ready = value
            elif kind in _MANAGEMENT_REPLIES:
                if life.quiet:
                    return None
                kind, value = self._decode_management(kind, value, payload)
            elif kind in ('assistant', 'assistant_error', 'assistant_cancelled'):
                import json
                from goal2.game.season import canonical_hash
                pending = self._assistant_request
                if (pending is None or not isinstance(value, dict)
                        or type(value.get('request')) is not int or value['request'] != pending[0]):
                    raise ProtocolError('stale or unexpected assistant reply')
                if kind == 'assistant':
                    if set(value) != {'request', 'input_hash', 'output_hash', 'result'} or value['input_hash'] != pending[1]:
                        raise ProtocolError('invalid assistant input binding')
                    try:
                        state = json.loads(payload.decode('utf8'))
                    except (ValueError, UnicodeDecodeError) as exc:
                        raise ProtocolError('invalid assistant state payload') from exc
                    result = value['result']
                    if (not isinstance(state, dict) or state.get('schema') != 'original_match.state/2'
                            or value['output_hash'] != canonical_hash(state)
                            or not isinstance(result, dict)
                            or set(result) != ({'allowed', 'refusal', 'country', 'manager', 'squad', 'pool', 'changed', 'recruited', 'calls'}
                                               | ({'extra_squad'} if len(pending)>2 and pending[2] else set()))
                            or type(result['allowed']) is not bool or type(result['changed']) is not bool
                            or result['refusal'] not in (None, 'finals', 'tour')
                            or result['allowed'] != (result['refusal'] is None)
                            or type(result['country']) is not int or not 1 <= result['country'] <= 128
                            or type(result['manager']) is not int or not 1 <= result['manager'] <= 6
                            or any(not isinstance(result[k], list)
                                   or any(type(w) is not int or not 1 <= w <= 3060 for w in result[k])
                                   for k in ('squad', 'pool', 'recruited'))
                            or len(result['squad']) != 20 or len(result['pool']) != 80
                            or len(set(result['squad'] + result['pool'])) != 100
                            or len(set(result['recruited'])) != len(result['recruited'])
                            or not set(result['recruited']) <= set(result['squad'])
                            or not isinstance(result['calls'], dict)
                            or any(not isinstance(k, str) or type(n) is not int or n < 1
                                   for k,n in result['calls'].items())):
                        raise ProtocolError('invalid assistant result')
                    extra_places=pending[2] if len(pending)>2 else 0
                    if extra_places:
                        extra=result['extra_squad']
                        if (not isinstance(extra,list) or len(extra)!=extra_places
                                or any(w is not None and (type(w) is not int or w not in result['pool']) for w in extra)
                                or len(set(w for w in extra if w is not None))!=sum(w is not None for w in extra)
                                or (not result['allowed'] and any(w is not None for w in extra))):
                            raise ProtocolError('invalid additional assistant selection')
                    result['state'] = state
                elif (payload or set(value) != ({'request', 'error'} if kind == 'assistant_error' else {'request'})
                      or (kind == 'assistant_error' and not isinstance(value['error'], str))):
                    raise ProtocolError('invalid assistant terminal reply')
                if self._assistant_cancelled:
                    kind, value = 'assistant_cancelled', {'request': pending[0]}
                self._assistant_request = None
                self._assistant_cancelled = False
            elif kind in ('season', 'season_error'):
                import json
                pending = self._season_request
                if (pending is None or not isinstance(value, dict)
                        or type(value.get('request')) is not int or value['request'] != pending[0]):
                    raise ProtocolError('stale or unexpected season reply')
                if kind == 'season_error':
                    if (set(value) != {'request', 'error', 'lost'} or not isinstance(value['error'], str)
                            or type(value['lost']) is not bool or payload):
                        raise ProtocolError('invalid season error reply')
                    if value['lost']:
                        self._season_active = False
                else:
                    if value.get('action') != pending[1]:
                        raise ProtocolError('season reply is for another operation')
                    if pending[1] in ('open', 'advance', 'observe', 'resume', 'preview', 'stopped_preview','completed_preview'):
                        try:
                            value['state'] = json.loads(payload.decode('utf8'))
                        except (ValueError, UnicodeDecodeError) as exc:
                            raise ProtocolError('invalid season state payload') from exc
                        from goal2.game.season import canonical_hash
                        if pending[1] == 'completed_preview':
                            from goal2.game.completed_view import CompletedMatchSnapshot
                            try:
                                meta=value.get('preview',{})
                                CompletedMatchSnapshot.from_packet(value,request=pending[0],
                                    managed_country=meta.get('managed_country'),
                                    event_count=self._season_pitch_events if self._season_pitch else None,
                                    frame_sequence=self._season_pitch_sequence if self._season_pitch else None)
                            except (ValueError,TypeError,AttributeError) as exc:
                                raise ProtocolError('invalid season completed preview') from exc
                        elif pending[1] == 'stopped_preview':
                            from goal2.game.stopped_snapshot import StoppedMatchSnapshot
                            try:
                                meta=value.get('preview',{})
                                StoppedMatchSnapshot.from_packet(value,request=pending[0],decision=pending[2],
                                    managed_country=meta.get('managed_country'),data=value.get('data'))
                            except (ValueError,TypeError,AttributeError) as exc:
                                raise ProtocolError('invalid season stopped preview') from exc
                        elif pending[1] == 'preview':
                            preview = value.get('preview')
                            if (set(value) != {'request', 'action', 'preview', 'state'}
                                    or not isinstance(preview, dict)
                                    or set(preview) != {'schema', 'decision', 'state_hash'}
                                    or preview['schema'] != 'goal2/prematch-preview/1'
                                    or type(preview['decision']) is not int
                                    or preview['decision'] != pending[2]
                                    or not isinstance(value['state'], dict)
                                    or value['state'].get('schema') != 'original_match.state/2'
                                    or preview['state_hash'] != canonical_hash(value['state'])):
                                raise ProtocolError('invalid season pre-match preview')
                        else:
                            observation = value.get('observation')
                            if (not isinstance(observation, dict)
                                    or observation.get('output_hash') != canonical_hash(value['state'])):
                                raise ProtocolError('season state differs from its observation')
                            # [designed: T170t/#751] Restore raw cells only on
                            # boundary observations, never preview or saves.
                            from goal2.game.season_wire import decode_observation
                            try:
                                value['observation'] = decode_observation(observation)
                            except ValueError as exc:
                                raise ProtocolError('invalid season news snapshot') from exc
                    elif payload:
                        raise ProtocolError('unexpected season reply payload')
                    if pending[1]=='next':
                        if self._season_pitch:
                            from goal2.game.season_pitch import validate_batch
                            try:
                                sequence,watermark,total=validate_batch(value,self._season_pitch_sequence,
                                    self._season_pitch_watermark,self._season_pitch_events,self._season_pitch_limit)
                            except ValueError as exc:raise ProtocolError('invalid native pitch batch') from exc
                            self._season_pitch_sequence,self._season_pitch_watermark,self._season_pitch_events=sequence,watermark,total
                        elif 'frames' in value or 'event_count' in value:
                            raise ProtocolError('unsolicited native pitch batch')
                    elif pending[1]=='configure':
                        self._season_pitch=self._season_pitch_pending
                        self._season_pitch_sequence=self._season_pitch_watermark=self._season_pitch_events=0
                    elif pending[1]=='pause':
                        expected={'request','action','paused'}
                        if value.get('paused') is False:expected.add('reason')
                        if (set(value)!=expected or type(value.get('paused')) is not bool
                                or (not value['paused'] and not isinstance(value.get('reason'),str))):
                            raise ProtocolError('invalid native pause acknowledgement')
                    elif pending[1] in ('open','discard','resume'):self._reset_season_pitch()
                    if pending[1] == 'open':
                        self._season_active = True
                        self._game = None
                    elif pending[1] == 'discard':
                        self._season_active = False
                self._season_request = None
            elif kind in ("opened",):
                value = None
            elif kind == "event":
                value = _event(value,live_players=getattr(self,"_live_players",False),
                               substitution_control=getattr(self,"_substitution_control",False),
                               selection=getattr(self,"_selected_bench",None))
                self._running(kind)
                self._events.append(value)
            elif kind == "frame":
                from goal2.game.watched_pitch import validate
                self._running(kind)
                validate(value, self._frame_sequence, self._frame_watermark)
                self._frame_sequence += 1
                self._frame_watermark = value["watermark"]
            elif kind == "decision":
                self._running(kind)
                if set(value) != {"decision", "event"} or type(value["decision"]) is not int:
                    raise ProtocolError("invalid decision reply")
                value = {"decision": value["decision"], "event": _event(value["event"],live_players=getattr(self,"_live_players",False),
                               substitution_control=getattr(self,"_substitution_control",False),
                               selection=getattr(self,"_selected_bench",None))}
            elif kind == "answered":
                self._running(kind)
                value = _report(value)
            elif kind == "pause_dropped":
                self._running(kind)
                if type(value) is not int:
                    raise ProtocolError("invalid pause_dropped reply")
            elif kind == "complete":
                from goal2.game.watched_match import WatchedOutcome
                self._running(kind)
                if set(value) != {"result", "events", "seeds", "engine_year"}:
                    raise ProtocolError("invalid complete reply")
                value = WatchedOutcome(value["result"], payload, tuple(_event(e,live_players=getattr(self,"_live_players",False),
                               substitution_control=getattr(self,"_substitution_control",False),
                               selection=getattr(self,"_selected_bench",None)) for e in value["events"]),
                                       tuple(value["seeds"]), value["engine_year"])
                if list(value.events) != self._events:
                    raise ProtocolError("the completed match differs from the events streamed")
                selection = getattr(self, "_selected_bench", None)
                if selection is not None:
                    from goal2.game.extended_schema import validate_extended_result
                    validate_extended_result(value.result, selection, competitive=selection.kind != 1)
                # [designed: T199, #627] Do not publish before the transcript is confirmed.
                self._completion = value
                self._match = None
                self._completion_timer = threading.Timer(self.cancel_deadline, self._overdue, args=(self._matches,))
                self._completion_timer.daemon = True
                self._completion_timer.start()
                return None
            elif kind == "settled":
                if self._completion is None or value is not None or payload:
                    raise ProtocolError("invalid completion confirmation")
                cancelled = self._cancelled_completion
                value = self._take_completion()
                if cancelled:
                    kind, value = "cancelled", None
                else:
                    kind = "complete"
            elif kind == "cancelled":
                self._running(kind)
                value = None
                self._match = None
                self._selected_bench = None
            elif kind == "error":
                if self._management_request is not None:
                    raise ProtocolError(f'unbound error during {self._management_request[0]} request')
                if self._assistant_request is not None:
                    raise ProtocolError('unbound error during assistant request')
                if not isinstance(value, str):
                    raise ProtocolError("invalid error reply")
                self._match = None
                self._take_completion()
            else:
                raise ProtocolError(f"unknown engine reply: {kind!r}")
        return kind, value

    def _take_completion(self):
        """Called under the lifecycle lock: consume or discard the held result."""
        value, self._completion = self._completion, None
        self._selected_bench = None
        self._cancelled_completion = False
        timer, self._completion_timer = self._completion_timer, None
        if timer is not None:
            timer.cancel()
        return value

    def _running(self, kind):
        if self._match is None:
            raise ProtocolError(f"engine reply {kind!r} with no match running")

    def _deliver(self, kind, value):
        try:
            self.on_reply(kind, value)
        except Exception:  # noqa: BLE001 - the window's callback must not end the reader
            import traceback
            traceback.print_exc(file=sys.stderr)
