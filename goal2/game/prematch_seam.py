"""[designed: T170i/T170k, #718/#726] The window's pre-kick-off edits over the held-Match seam.

The adapter owns no Match lifecycle and no policy: the SeasonSession holds the pending
route Match (T170b), and this maps the window's S10/S08 pre-kick-off actions one answer
at a time onto T132 part 1's pre-match decision (archaeology #711 at 39a84174, vendored
by T170h/T170j) — the original itself makes every edit through its own DEA6 route.

[confirmed: vendored match.py, configure_route_entry] Configuration is exactly once,
before any event runs; a failed validation consumes nothing. [confirmed: archaeology
tests/test_route_prematch_input_t132.py] The pre-match decision takes tactics and/or
within-twenty swap pairs edit_only, an empty answer plays, and an edited answer returns
a fresh `pre_match` decision. The pool exchange stays a named refusal until upstream
T132's pool arm is vendored (T170i scope 4: never a silent drop).
"""

# [designed: T170i scope 4] The named refusal the pool control shows while the seam's
# second half (upstream T132's pool arm, archaeology #709) is not vendored into the kit.
POOL_EXCHANGE_NOT_VENDORED = ('the pool exchange has no seam arm yet: archaeology T132\'s pool '
                              'arm is not vendored (upstream #709; never a silent drop)')


class PrematchSeam:
    """The window's pre-kick-off sequence on one held pending route Match."""

    def __init__(self, match, captain=None, substitutions=None):
        # [T170i scope 1] Configure exactly once, before any event runs; the flags are the
        # seam's fixed inputs, the captain/budget the window's S16/fixture choices.
        match.configure_route_entry(captain=captain, substitutions=substitutions,
                                    pre_match_edits=True, live_players=True, set_piece=True,
                                    substitution_control=True, record_draws=True)
        self.match = match

    def set_team_tactic(self, element, value):
        """[T170i scope 2] S10's team-tactics control: one element 1..8 to its window value."""
        self.match.answer(edit_only=True, tactics={int(element): bool(value)})

    def swap(self, outgoing, incoming):
        """[T170i scope 2] S08's swap: one within-twenty pair (the kit's generic membership rule)."""
        self.match.answer(edit_only=True, substitutions=[[int(outgoing), int(incoming)]])

    def exchange(self, outgoing, incoming):
        """[T170i scope 4] The pool control: a named refusal until the pool arm is vendored."""
        raise ValueError(f'{POOL_EXCHANGE_NOT_VENDORED} (exchange {outgoing}, {incoming} refused)')

    def play(self):
        """[T170i scope 3] Kick-off: the empty answer; the declared captain already stands."""
        self.match.answer()
