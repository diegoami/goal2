"""[designed: T170aj/T170an/T170aq] Guard single edits at a legal stopped bench."""


def validate_edit(data, answer):
    """Check the public decision domain before the SDK consumes the answer."""
    if (data.get('context') != 'half_time' or data.get('substitutions_now') is not True
            or answer.get('edit_only') is not True):
        raise ValueError('Changes are unavailable at this stop.')
    if set(answer) == {'edit_only', 'tactics'}:
        return validate_tactic(answer['tactics'])
    _validate_bench_edit(data, answer)


def extra_time_half(data):
    """[confirmed: Match._on_team_menu] The SDK publishes one of two stops."""
    half = data.get('half')
    if data.get('context') != 'extra_time' or type(half) is not int or half not in (1, 2):
        raise ValueError('An extra-time stop needs an exact half.')
    return half


def validate_extra_time(data, answer):
    """[confirmed: #679/#680] One tactics-only edit at either verified half."""
    extra_time_half(data)
    if set(answer) != {'edit_only', 'tactics'} or answer['edit_only'] is not True:
        raise ValueError('Send only one extra-time team tactic.')
    validate_tactic(answer['tactics'])


def validate_tactic(values):
    if isinstance(values, dict) and len(values) == 1:
        element, value = next(iter(values.items()))
        # The worker receives map keys through JSON.
        if (type(value) is bool
                and ((type(element) is int and 1 <= element <= 8)
                     or (type(element) is str and len(element) == 1 and element in '12345678'))):
            return
    raise ValueError('Choose one team tactic.')


def validate_substitution(data, answer):
    """[confirmed: Match.answer/#695] One legal in-match edit without Play."""
    if data.get('context') != 'substitution' or data.get('substitutions_now') is not True:
        raise ValueError('A substitution is unavailable at this stop.')
    _validate_bench_edit(data, answer)


def _validate_bench_edit(data, answer):
    if set(answer) == {'edit_only', 'positions'} and answer['edit_only'] is True:
        positions = answer['positions']
        if isinstance(positions, dict) and len(positions) == 1:
            word, position = next(iter(positions.items()))
            # [confirmed: Match.answer] Live position goals are numeric.
            if _current_player(data, word) and type(position) is int and 0 <= position <= 13:
                return
        raise ValueError('Choose one current managed player and a position from 0 to 13.')
    if set(answer) == {'edit_only', 'own_tactics'} and answer['edit_only'] is True:
        choices = answer['own_tactics']
        if isinstance(choices, dict) and len(choices) == 1:
            word, tactics = next(iter(choices.items()))
            if _current_player(data, word) and isinstance(tactics, dict) and len(tactics) == 1:
                element, value = next(iter(tactics.items()))
                if (type(element) is int and 1 <= element <= 4
                        or type(element) is str and element in ('1', '2', '3', '4')):
                    if value is None or type(value) is bool:
                        return
        raise ValueError('Choose one current managed player and one own tactic.')
    _validate_pair(data, answer)


def _current_player(data, word):
    if type(word) is str and 1 <= len(word) <= 4 and word[0] != '0' and word.isascii() and word.isdecimal():
        word = int(word)
    return type(word) is int and word > 0 and word in data['eleven'] + data['bench']


def _validate_pair(data, answer):
    if set(answer) != {'edit_only', 'substitutions'} or answer['edit_only'] is not True:
        raise ValueError('Send only one substitution.')
    pairs = answer['substitutions']
    if (not isinstance(pairs, list) or len(pairs) != 1 or not isinstance(pairs[0], list)
            or len(pairs[0]) != 2 or any(type(word) is not int or word <= 0 for word in pairs[0])):
        raise ValueError('Choose one outgoing and one incoming player.')
    outgoing, incoming = pairs[0]
    if outgoing not in data['eleven'] or incoming not in data['bench']:
        raise ValueError('Choose an outgoing starter and an incoming bench player.')
    if data['substitutions_left'] <= 0:
        raise ValueError('No substitutions remain.')
    # [confirmed: Match._available] Availability comes from this decision's live player record.
    record = bytes.fromhex(dict(data['player_records']).get(incoming, ''))
    if len(record) != 20 or not 0 < record[14] < 128 or record[16] & 0xA4:
        raise ValueError('That bench player is unavailable.')
