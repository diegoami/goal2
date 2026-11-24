"""[designed: T170al] Guard ordinary paused substitution request edits."""


def validate_request_edit(data, answer):
    """[confirmed: archaeology #695/#696] Only the desired latch is submitted."""
    if (data.get('context') != 'pause' or data.get('substitutions_now') is not False
            or type(data.get('request_substitution')) is not bool):
        raise ValueError('A substitution request is unavailable at this stop.')
    if (set(answer) != {'edit_only', 'request_substitution'} or answer['edit_only'] is not True
            or type(answer['request_substitution']) is not bool):
        raise ValueError('Send only a request or cancel at this pause.')
