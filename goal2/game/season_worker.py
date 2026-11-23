"""[designed: T170o/#735] Child-owned season operations on the existing engine pipe.

[confirmed: T170b/T170n] The session and PrematchSeam retain the actual route Match.
No window policy, reconstructed Match, private engine writes or implicit answers.
"""
from copy import deepcopy
from dataclasses import asdict

from goal2.game.season import SeasonSession, canonical_hash
from goal2.game.prematch_seam import PrematchSeam

FIELDS = {'open': {'state', 'keys'}, 'advance': set(), 'observe': set(),
          'configure': {'captain', 'substitutions','frames'}, 'next': {'count'},
          'answer': {'decision', 'answer'}, 'preview': {'decision'}, 'stopped_preview': {'decision'},
          'pause': set(), 'completed_preview': set(), 'resume': set(), 'discard': set()}
ANSWER_FIELDS = {'substitutions', 'tactics', 'positions', 'marking', 'own_tactics',
                 'quick', 'speed', 'shootout_order', 'taker', 'edit_only',
                 'request_substitution', 'opportunity', 'captain'}


class SeasonRequestError(ValueError):
    """A known pure request-validation refusal; the session stays held."""


def validate_request(header):
    action = header.get('action')
    if (header.get('op') != 'season' or type(header.get('request')) is not int
            or header['request'] < 1 or not isinstance(action, str) or action not in FIELDS
            or set(header) - ({'op', 'request', 'action'} | FIELDS[action])):
        raise SeasonRequestError('invalid season request')
    if action in ('preview','stopped_preview') and (type(header.get('decision')) is not int or header['decision'] < 1):
        raise SeasonRequestError('preview needs a positive decision number')
    if action=='configure' and type(header.get('frames',False)) is not bool:
        raise SeasonRequestError('frames must be boolean')
    return action


class SeasonWorker:
    def __init__(self):
        self.session = None
        self._reset_match()
        self._decision_number = 0

    def _reset_match(self):
        self.seam = self.stream = None
        self.decision = None
        self.exhausted = False
        self.frames=False;self.frame_sequence=0;self.frame_watermark=0;self.event_count=0

    def dispatch(self, header):
        action = validate_request(header)
        result = {'request': header['request'], 'action': action}
        if action == 'discard':
            self.session = None
            self._reset_match()
            return result
        if action == 'open':
            # Construct/validate before replacing the current holding.
            session = SeasonSession(header.get('state'), keys=header.get('keys'))
            self.session = session
            self._reset_match()
        elif self.session is None:
            raise SeasonRequestError('no season is open; explicitly open a state/2')
        session = self.session
        observation = None
        if action == 'advance':
            if session.pending_match is not None:
                raise SeasonRequestError('complete and resume the held match before advancing')
            observation = session.advance()
            self._reset_match()
        elif action in ('configure', 'next', 'answer', 'preview', 'stopped_preview', 'completed_preview', 'pause', 'resume'):
            match = session.pending_match
            if match is None:
                raise SeasonRequestError('no season match is pending')
            if action == 'configure':
                if self.seam is not None:
                    raise SeasonRequestError('the held match is already configured')
                self.seam = PrematchSeam(match, captain=header.get('captain'),
                                         substitutions=header.get('substitutions'),frames=header.get('frames',False))
                self.frames=header.get('frames',False)
                self.stream = iter(match.events())
            elif action == 'next':
                count = header.get('count', 32)
                if type(count) is not int or not 1 <= count <= 32:
                    raise SeasonRequestError('season event count must be 1..32')
                if self.stream is None or self.decision is not None:
                    raise SeasonRequestError('configure the match and answer its waiting decision first')
                events = []
                frames=[]
                for _ in range(count):
                    try:
                        event = next(self.stream)
                    except StopIteration:
                        self.exhausted = True
                        break
                    if self.frames and event.kind=='tick':
                        from goal2.game.watched_pitch import snapshot,validate
                        frame=snapshot(match,event,self.frame_sequence,self.event_count)
                        validate(frame,self.frame_sequence,self.frame_watermark)
                        frames.append(frame);self.frame_sequence+=1;self.frame_watermark=frame['watermark']
                        continue
                    events.append(asdict(event));self.event_count+=1
                    if event.kind == 'decision':
                        self._decision_number += 1
                        self.decision = self._decision_number
                        break
                result.update(events=events, decision=self.decision, over=match.over,
                              exhausted=self.exhausted)
                if self.frames:result.update(frames=frames,event_count=self.event_count)
            elif action=='pause':
                if self.seam is None or not self.frames or self.exhausted or self.decision is not None:
                    raise SeasonRequestError('pause needs an active sampled match without a waiting decision')
                from goal2.engine.original_match.match import MatchError
                try:match.pause()
                except MatchError as exc:result.update(paused=False,reason=str(exc))
                else:result.update(paused=True)
            elif action == 'completed_preview':
                # [confirmed: T170ag/a492059d] Current completed records and
                # the recorded whistle board are distinct public reads.
                if (self.seam is None or self.stream is None or not match.over or not self.exhausted
                        or self.decision is not None or match.waiting is not None):
                    raise SeasonRequestError('completed preview needs the drained completed match')
                from goal2.game.completed_view import completed_result_hash
                current=match.records_after();completed=deepcopy(match.result())
                result.update(state=current,result=completed,preview=dict(schema='goal2/completed-preview/1',
                    managed_country=match.opts['managed'],event_count=self.event_count,frame_sequence=self.frame_sequence,
                    state_hash=canonical_hash(current),result_hash=completed_result_hash(completed)))
            elif action == 'stopped_preview':
                # [confirmed: T170ae, archaeology87d92501] Both public reads
                # observe the stopped generator; neither runs it or publishes.
                from goal2.game.stopped_snapshot import CONTEXTS
                if (self.seam is None or self.decision is None
                        or header['decision'] != self.decision or match.waiting is None
                        or match.waiting.get('context') not in CONTEXTS):
                    raise SeasonRequestError('stopped preview needs the current in-match decision')
                current=match.records_after();data=deepcopy(match.waiting)
                result.update(preview=dict(schema='goal2/stopped-preview/1',decision=self.decision,
                    managed_country=match.opts['managed'],state_hash=canonical_hash(current),
                    data_hash=canonical_hash(data)),state=current,data=data)
            elif action == 'preview':
                # [designed: T170s/#746; confirmed: T170r audit, fb6d3093]
                # Read current records without consuming the stopped generator.
                # A preview never changes the session's route-boundary state.
                if (self.seam is None or self.decision is None
                        or type(header.get('decision')) is not int
                        or header['decision'] != self.decision
                        or match.waiting is None or match.waiting.get('context') != 'pre_match'):
                    raise SeasonRequestError('preview needs the current pre-match decision')
                current = match.records_after()
                result.update(preview={'schema': 'goal2/prematch-preview/1',
                                       'decision': self.decision, 'state_hash': canonical_hash(current)},
                              state=current)
            elif action == 'answer':
                answer = header.get('answer')
                if (self.decision is None or type(header.get('decision')) is not int
                        or header['decision'] != self.decision):
                    raise SeasonRequestError('stale or consumed season decision')
                if not isinstance(answer, dict) or set(answer) - ANSWER_FIELDS:
                    raise SeasonRequestError('invalid season answer')
                answer = deepcopy(answer)
                # [designed: packet JSON] JSON object keys are text, Match expects integer elements.
                for field in ('tactics', 'positions', 'marking', 'own_tactics'):
                    if field in answer and isinstance(answer[field], dict):
                        try:
                            answer[field] = {int(k): v for k, v in answer[field].items()}
                        except (TypeError, ValueError) as exc:
                            raise SeasonRequestError('invalid season answer element') from exc
                try:
                    match.answer(**answer)
                except ValueError as exc:
                    # [confirmed: archaeology T133-T137/#715/#717/#720/#722/#724] These input
                    # validations precede guest/replay consumption. A bad roster
                    # pair, position, own/marking value or captain can repair the same decision.
                    if ('captain' in answer or (('substitutions' in answer or 'positions' in answer
                                                or 'own_tactics' in answer or 'marking' in answer)
                                               and match.waiting is not None
                                               and match.waiting.get('context') == 'pre_match')):
                        raise SeasonRequestError(str(exc)) from exc
                    raise
                self.decision = None
            else:
                if not match.over or not self.exhausted or self.decision is not None:
                    raise SeasonRequestError('the held match is incomplete or has unread events')
                observation = session.resume(match)
                self._reset_match()
        if action in ('open', 'advance', 'observe', 'resume'):
            result.update(observation=asdict(observation or session.observe()), state=session.state)
        return deepcopy(result)
