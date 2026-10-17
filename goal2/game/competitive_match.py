"""[designed: T51; confirmed: PR255/E034 at424d599] Original competitive execution, owner budget5/5."""
from goal2.game.watched_match import _prepare_match, _drive_match


def prepare_competitive(state,original,fixture):
    """[designed] Validate a private source-fixture image; public friendlies stay separate."""
    return _prepare_match(state,original,fixture,competitive=True)


def run_competitive_match(state,original,fixture,*,reference_seed=None,delay_byte=None,
                          record_draws=False,quick_at_half_time=False):
    """[designed: owner#73] Complete original play with explicit5 substitutions on both sides.
    [confirmed: E034] Quick at half time is an explicit diagnostic policy, not a live control.
    """
    if type(quick_at_half_time) is not bool:raise ValueError('quick_at_half_time must be boolean')
    image=prepare_competitive(state,original,fixture)
    return _drive_match(state,image,fixture,reference_seed=reference_seed,delay_byte=delay_byte,
                        record_draws=record_draws,substitutions=(5,5),quick_at_half_time=quick_at_half_time)
