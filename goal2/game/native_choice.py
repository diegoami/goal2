"""[designed: T170ak/T170am] Exact native chooser and opportunity inputs."""


def opportunity_duration(data):
    """[confirmed: archaeology #695/#696] Original notice time in milliseconds."""
    keeper = data.get('keeper_unavailable')
    polls, ms = data.get('timeout_polls'), data.get('poll_ms')
    if (type(keeper) is not bool or type(polls) is not int or type(ms) is not int
            or polls != (1000 if keeper else 400) or ms != 10):
        raise ValueError('invalid original opportunity timing')
    return polls * ms


def validate_choice(data, answer):
    """Check the chooser's answer against the current public SDK domain."""
    context = data.get('context')
    if context == 'substitution_opportunity':
        opportunity_duration(data)
        if (type(data.get('substitutions_now')) is bool and set(answer) == {'opportunity'}
                and type(answer['opportunity']) is str
                and answer['opportunity'] in ('accept', 'timeout')):
            return
        raise ValueError('The substitution prompt takes an accepting key or a timeout.')
    if context == 'set_piece' and set(answer) == {'taker'}:
        word = answer['taker']
        if word is None or (type(word) is int and word in data['available']):
            return
    if context == 'shootout_order' and set(answer) == {'shootout_order'}:
        order = answer['shootout_order']
        if (type(order) is list and len(order) <= data['takers']
                and all(type(word) is int and word in data['available'] for word in order)
                and len(order) == len(set(order))):
            return
    raise ValueError('Choose from the available players at this stop.')
