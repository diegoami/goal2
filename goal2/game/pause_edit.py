"""[designed: T170al/T170ap] Guard disjoint edits at an ordinary pause."""

from goal2.game.half_time_edit import validate_tactic


def validate_pause_edit(data, answer):
    if set(answer) == {'edit_only', 'tactics'}:
        # [confirmed: #679/#680] The team menu is legal independently of SELECT TEAM.
        if data.get('context') != 'pause' or answer['edit_only'] is not True:
            raise ValueError('A team tactic requires a current ordinary pause.')
        return validate_tactic(answer['tactics'])
    validate_request_edit(data, answer)


def validate_request_edit(data, answer):
    """[confirmed: archaeology #695/#696] Only the desired latch is submitted."""
    if (data.get('context') != 'pause' or data.get('substitutions_now') is not False
            or type(data.get('request_substitution')) is not bool):
        raise ValueError('A substitution request is unavailable at this stop.')
    if (set(answer) != {'edit_only', 'request_substitution'} or answer['edit_only'] is not True
            or type(answer['request_substitution']) is not bool):
        raise ValueError('Send only a request or cancel at this pause.')
