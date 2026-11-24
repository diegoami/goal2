"""[designed: T170i/T170k/T170m, #718/#726] The window's pre-kick-off edits over the held-Match seam.

The adapter owns no Match lifecycle and no policy: the SeasonSession holds the pending
route Match (T170b), and this maps the window's S10/S08 pre-kick-off actions one answer
at a time onto T132's pre-match decision (archaeology #711/#713 at e02711cb, vendored by
T170h/T170j/T170l) — the original itself makes every edit through its own DEA6 route.

[confirmed: vendored match.py, configure_route_entry] Configuration is exactly once,
before any event runs; a failed validation consumes nothing. [confirmed: archaeology
tests/test_route_prematch_input_t132.py] The pre-match decision takes tactics and/or swap
pairs within the twenty or out of the made pool edit_only, an empty answer plays, and an
edited answer returns a fresh `pre_match` decision. [T170m] The pool exchange is the seam's
own answer now that T170l vendored the pool arm; T170k's named refusal retired with it.
[confirmed: T135/fc6b5294; T170u] Numeric positions use original R across squad/pool;
an explicit club action uses original C, even when the position is already equal.
[confirmed: T136/46315dcf; T170v] Own tactics preserve explicit off/on/inherit
through the original T menu across squad/pool, using player-country defaults.
[confirmed: T137/87d92501; T170w] Marking distinguishes inherit from explicit
protected zone and opponent goals for eligible current squad, including bench.
"""


# [designed: T170p] Explicit None asks for the original default; omission keeps
# the initial captain configuration. Only plain JSON values cross the worker.
_UNSET_CAPTAIN = object()


class PrematchSeam:
    """The window's pre-kick-off sequence on one held pending route Match."""

    def __init__(self, match, captain=None, substitutions=None, *, frames=False, post_match_review=False):
        # [T170i scope 1] Configure exactly once, before any event runs; the flags are the
        # seam's fixed inputs, the captain/budget the window's S16/fixture choices.
        if type(frames) is not bool:raise ValueError('frames must be boolean')
        # [confirmed: T127, match87d92501] Declare tick stops before execution;
        # default kwargs stay identical, never patch a running Match's options.
        options = {'ticks': True} if frames else {}
        if type(post_match_review) is not bool:
            raise ValueError('post_match_review must be boolean')
        if post_match_review:
            options['post_match_review'] = True
        match.configure_route_entry(captain=captain, substitutions=substitutions,
                                    pre_match_edits=True, live_players=True, set_piece=True,
                                    substitution_control=True, record_draws=True, **options)
        self.match = match

    def set_team_tactic(self, element, value):
        """[T170i scope 2] S10's team-tactics control: one element 1..8 to its window value."""
        self.match.answer(edit_only=True, tactics={int(element): bool(value)})

    def swap(self, outgoing, incoming):
        """[T170q/T134] S08's full-squad pair; fresh decisions retain the original's sorted order."""
        self.match.answer(edit_only=True, substitutions=[[int(outgoing), int(incoming)]])

    def exchange(self, outgoing, incoming):
        """[T170q/T134, T170i scope 4] The pool control: any squad player out, a made-pool word in —
        the kit's pre-match arm accepts a pool word as the incoming (archaeology #713's DEA6
        pool pane route; the pool is published in the decision beside the bench)."""
        self.match.answer(edit_only=True, substitutions=[[int(outgoing), int(incoming)]])

    def set_position(self, player, position):
        """[confirmed: T135/fc6b5294, F010] Numeric0..13 goal through native R."""
        if type(position) is not int or not 0 <= position <= 13:
            raise ValueError('position must be an integer code0..13')
        self.match.answer(edit_only=True, positions={player: position})

    def club_position(self, player):
        """[confirmed: T135/fc6b5294] Native C once, including already-equal values."""
        self.match.answer(edit_only=True, positions={player: 'club'})

    def set_own_tactic(self, player, element, value):
        """[confirmed: T136/46315dcf, F010] Native own row1..4, exact False/True/None."""
        if type(element) is not int or not 1 <= element <= 4:
            raise ValueError('own tactic element must be integer1..4')
        if value is not None and type(value) is not bool:
            raise ValueError('own tactic value must be False, True or None')
        self.match.answer(edit_only=True, own_tactics={player: {element: value}})

    def set_marking(self, player, target):
        """[confirmed: T137/87d92501, F010] Native row5: None/zone0/opponent."""
        if target is not None and type(target) is not int:
            raise ValueError('marking target must be None, integer0 or an opponent word')
        self.match.answer(edit_only=True, marking={player: target})

    def play(self, *, captain=_UNSET_CAPTAIN):
        """[T170p/T133] Play after edits: optional current-XI captain, or None for
        the original default. Omission retains the initial declared captain."""
        if captain is _UNSET_CAPTAIN:
            self.match.answer()
        else:
            self.match.answer(captain=captain)
