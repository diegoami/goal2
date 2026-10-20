"""[designed: T86] Opt-in fictional scenario lane over the existing desktop seams.

Nothing here is original data or an original rule. Every name, number and score
is invented by a closed formula or a fixed script, so the lane runs with no
original resources and no optional runtime. See docs/cloud-270/seam.md.

The lane is never a production fallback: `goal2.desktop` does not import it.
"""
MARK = 'goal2-fictional-scenario/1'
ENGINE = 'goal2-scenario:fictional:1'
# [designed: T86] Template marker bytes; deliberately not a zip/savestate.
TEMPLATE = b'GOAL2 FICTIONAL SCENARIO v1: not a savestate, never a career template\n'


def is_scenario(value):
    """[designed: T86] True for a marked scenario state or for an owner holding one."""
    state = getattr(value, 'state', value)
    return getattr(state, 'scenario', None) == MARK


def require_scenario(value, action):
    """[designed: T86] Refuse to let fictional machinery touch an unmarked game."""
    if not is_scenario(value):
        raise ValueError(f'{action} refused: not a fictional scenario game')
