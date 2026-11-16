"""[designed: T170o/#735] Child-owned season operations on the existing engine pipe.

[confirmed: T170b/T170n] The session and PrematchSeam retain the actual route Match.
No window policy, reconstructed Match, private engine writes or implicit answers.
"""
from copy import deepcopy
from dataclasses import asdict

from goal2.game.season import SeasonSession
from goal2.game.prematch_seam import PrematchSeam

FIELDS = {'open': {'state', 'keys'}, 'advance': set(), 'observe': set(),
          'configure': {'captain', 'substitutions'}, 'next': {'count'},
          'answer': {'decision', 'answer'}, 'resume': set(), 'discard': set()}
ANSWER_FIELDS = {'substitutions', 'tactics', 'positions', 'marking', 'own_tactics',
                 'quick', 'speed', 'shootout_order', 'taker', 'edit_only',
                 'request_substitution', 'opportunity'}


class SeasonRequestError(ValueError):
    """A request refused before entering engine code; the session stays held."""


def validate_request(header):
    action = header.get('action')
    if (header.get('op') != 'season' or type(header.get('request')) is not int
            or header['request'] < 1 or not isinstance(action, str) or action not in FIELDS
            or set(header) - ({'op', 'request', 'action'} | FIELDS[action])):
        raise SeasonRequestError('invalid season request')
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
        elif action in ('configure', 'next', 'answer', 'resume'):
            match = session.pending_match
            if match is None:
                raise SeasonRequestError('no season match is pending')
            if action == 'configure':
                if self.seam is not None:
                    raise SeasonRequestError('the held match is already configured')
                self.seam = PrematchSeam(match, captain=header.get('captain'),
                                         substitutions=header.get('substitutions'))
                self.stream = iter(match.events())
            elif action == 'next':
                count = header.get('count', 32)
                if type(count) is not int or not 1 <= count <= 32:
                    raise SeasonRequestError('season event count must be 1..32')
                if self.stream is None or self.decision is not None:
                    raise SeasonRequestError('configure the match and answer its waiting decision first')
                events = []
                for _ in range(count):
                    try:
                        event = next(self.stream)
                    except StopIteration:
                        self.exhausted = True
                        break
                    events.append(asdict(event))
                    if event.kind == 'decision':
                        self._decision_number += 1
                        self.decision = self._decision_number
                        break
                result.update(events=events, decision=self.decision, over=match.over,
                              exhausted=self.exhausted)
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
                match.answer(**answer)
                self.decision = None
            else:
                if not match.over or not self.exhausted or self.decision is not None:
                    raise SeasonRequestError('the held match is incomplete or has unread events')
                observation = session.resume(match)
                self._reset_match()
        if action in ('open', 'advance', 'observe', 'resume'):
            result.update(observation=asdict(observation or session.observe()), state=session.state)
        return deepcopy(result)
