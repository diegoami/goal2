"""[designed: T170aj/T170an] Guard single edits at a legal stopped bench."""


def validate_edit(data, answer):
    """Check the public decision domain before the SDK consumes the answer."""
    if (data.get('context') != 'half_time' or data.get('substitutions_now') is not True
            or answer.get('edit_only') is not True):
        raise ValueError('Changes are unavailable at this stop.')
    if set(answer) == {'edit_only', 'tactics'}:
        values = answer['tactics']
        if isinstance(values, dict) and len(values) == 1:
            element, value = next(iter(values.items()))
            # The worker receives map keys through JSON.
            if ((type(element) is int and 1 <= element <= 8)
                    or (type(element) is str and element in '12345678' and len(element) == 1)):
                if type(value) is bool:
                    return
        raise ValueError('Choose one team tactic.')
    _validate_pair(data, answer)


def validate_substitution(data, answer):
    """[confirmed: Match.answer/#695] One legal in-match pair without Play."""
    if data.get('context') != 'substitution' or data.get('substitutions_now') is not True:
        raise ValueError('A substitution is unavailable at this stop.')
    _validate_pair(data, answer)


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
