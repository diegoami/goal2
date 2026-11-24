"""[designed: T170ak] Exact answer shapes for the native chooser."""


def validate_choice(data, answer):
    """Check the chooser's answer against the current public SDK domain."""
    context = data.get('context')
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
