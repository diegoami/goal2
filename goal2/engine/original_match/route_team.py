"""T124t's route-harness team policy, not a decision made for goal2's player.

[designed: owner, 2026-11-04, goal2 #509] Before a managed match the harness uses the original's SELECT TEAM
screen to replace unavailable players. Choice: among legal elevens from the current twenty, keep as many existing
starters as possible, then choose the lexicographically first tuple of squad slots. Pair outgoing and incoming
players in squad order. The original sorts after every swap, so each key reads the live squad again.

[confirmed: F016/F029; named/seg_0791_12.c DEA6, seg_0791_13.c EA09; code/seg_1771_05.asm 3216-328E]
Availability: signed energy +0xE >0 and status +0x10 elements 8,6,3 clear. Valid eleven: eleven nonzero players,
exactly one goalkeeper (position +6 ==0), at most three of each other position 1..13. EA09 remains the original's
validator. DEA6 makes the swaps before play, with two Enters; no player, squad or status bytes are written here.
"""
from collections import Counter
from itertools import combinations

from . import screens as S
from .screens import MAX_MOVES, ScreenError
from .match import Match, MatchError, SITE_SELECT, PUSHED_BACK, KEY, PLAYER_ENERGY, PLAYER_STATUS, PLAYER_POSITION


def choose_eleven(squad, player):
    """Return (outgoing, incoming) player words using the policy above; no guest writes."""
    available = [i for i, w in enumerate(squad) if w and 0 < player(w, PLAYER_ENERGY) < 128
                 and not player(w, PLAYER_STATUS) & 0xA4 and 0 <= player(w, PLAYER_POSITION) <= 13]
    best = None
    for slots in combinations(available, 11):
        counts = Counter(player(squad[i], PLAYER_POSITION) for i in slots)
        if counts[0] != 1 or any(n > 3 for pos, n in counts.items() if pos):
            continue
        rank = (-sum(i < 11 for i in slots), slots)
        if best is None or rank < best:
            best = rank
    if best is None:
        raise ValueError("the squad has no legal eleven under the route harness policy")
    slots = best[1]
    outgoing = [w for i, w in enumerate(squad[:11]) if i not in slots]
    incoming = [squad[i] for i in slots if i >= 11]
    return list(zip(outgoing, incoming))


class PreMatchPlan(S.MenuPlan):
    """DEA6 before play, rather than E022's substitutions during play."""

    def __init__(self, side, tactics=None, subs=None, positions=None, marking=None, **kwargs):
        super().__init__(side, tactics=tactics, subs=subs, marking=marking, **kwargs)
        self.marking = dict(marking or {})
        self._mark_status = 0
        self._mark_pressed = self._mark_calls = 0
        self._mark_pending = False
        # [T135/#720] Preserve MenuPlan's sub/position/own order without
        # coercing the distinct native C action into a numeric R goal.
        at = next((i for i, job in enumerate(self.jobs) if job[0] == "own"), len(self.jobs))
        self.jobs[at:at] = [("position", int(p), c) for p, c in (positions or {}).items()]
        if positions and "select" not in self.steps:
            self.steps.insert(-1, "select")
        self._position_visit = None
        self._position_observed = False
        self._position_entered = False
        self._own_visit = None
        self._own_entered = self._own_returned = False
        self._own_initial = 0
        self.pool_pane = False          # the SELECT screen opens in the squad view (E009-r0001)
        self._expected_swap = None
        self._swap_observed = False

    def _expect_swap(self, s, job):
        # [confirmed: F031 DEA6/007B; T134] Exact word-list permutation before
        # either original sort. Sorting later preserves each block's membership.
        squad, pool = list(s["squad"]), list(s.get("pool", ()))
        i = squad.index(job[1])
        if job[2] in squad:
            j = squad.index(job[2]); squad[i], squad[j] = squad[j], squad[i]
        else:
            j = pool.index(job[2]); squad[i], pool[j] = pool[j], squad[i]
        self._expected_swap = (squad, [w for w in pool if w])
        self._swap_observed = False

    def observe_swap(self, s):
        if self.pending_check is None or self._expected_swap is None:
            raise MatchError("unexpected pre-match word swap")
        if (s["squad"], s.get("pool", [])) != self._expected_swap:
            raise MatchError("original pre-match word swap differs from requested pair")
        self._swap_observed = True

    def observe_position_entry(self, player, key):
        visit = self._position_visit
        if (visit is None or self._position_entered or player != visit[0]
                or key != (ord("C") if visit[2] else S.KEY_R)):
            raise MatchError("original pre-match position entry differs from requested input")
        self._position_entered = True

    def observe_position(self, player, position, key):
        if not self._position_entered or self._position_visit != (player, position, key):
            raise MatchError("original pre-match position return differs from requested input")
        self._position_observed = True

    def _position_key(self, s, job):
        player, goal = job[1:]
        in_pool = player not in s["squad"]
        if in_pool and player not in s.get("pool", ()):
            raise MatchError("pre-match position player left squad/pool")
        if self.pool_pane != in_pool:
            self.pool_pane = in_pool
            return self.act(S.LEFT)
        if in_pool:
            # [confirmed: F011/T128] Made-pool list index = scroll+cursor-2.
            here = s["pool_scroll"] + s["pool_cursor"]
            target = s["pool"].index(player) + 2
            if here != target:
                self.moves += 1
                if self.moves > 2 * MAX_MOVES:
                    raise ScreenError("pool cursor did not reach position player")
                return S.DOWN if here < target else S.UP
        else:
            target = s["squad"].index(player) + 1
            if s["cursor"] != target:
                return self.move(s["cursor"], target)
        if goal == "club":
            self._position_visit = (player, s["club_position"](player), ord("C"))
            return self.act(ord("C"))
        if s["position"](player) == goal:
            self.done.append(job)
            self._next_job()
            return self.select_key(s)
        # [confirmed: 1771:4925/4952] R wraps0..13 and clears A976 before return.
        self._position_visit = (player, (s["position"](player) + 1) % S.N_POSITIONS, 0)
        return self.act(S.KEY_R)

    def observe_own_entry(self, player, pane, key, own_set):
        if self._own_visit != (player, pane) or self._own_entered or key != S.KEY_T:
            raise MatchError("original pre-match own entry differs from requested input")
        self._own_entered = True
        self._own_initial = own_set

    def observe_own(self, player, pane, own_set, key, default):
        if not self._own_entered or self._own_visit != (player, pane) or key != S.ESC:
            raise MatchError("original pre-match own return differs from requested input")
        for element, goal in self.jobs[self.job][2].items():
            has = bool(own_set & (1 << (element + 3)))
            value = bool(own_set & (1 << (element - 1)))
            if goal is None:
                if has or (self._own_initial & (1 << (element + 3)) and
                           value != bool(default & (1 << (element - 1)))):
                    raise MatchError("original pre-match own inheritance was not reached")
            elif not has or value != goal:
                raise MatchError("original pre-match own value was not reached")
        self._own_returned = True

    def _own_select_key(self, s, job):
        player = job[1]
        if self.in_own:
            if not self._own_returned or self.own_failed:
                raise MatchError("original pre-match own input has no completed visit")
            self.done.append(job)
            self.in_own = False
            self._own_visit = None
            self._own_entered = self._own_returned = False
            self._next_job()
            return self.select_key(s)
        in_pool = player not in s["squad"]
        if in_pool and player not in s.get("pool", ()):
            raise MatchError("pre-match own player left squad/pool")
        if self.pool_pane != in_pool:
            self.pool_pane = in_pool
            return self.act(S.LEFT)
        if in_pool:
            here = s["pool_scroll"] + s["pool_cursor"]
            target = s["pool"].index(player) + 2  # F011/T128
            if here != target:
                self.moves += 1
                if self.moves > 2 * MAX_MOVES:
                    raise ScreenError("pool cursor did not reach own-tactic player")
                return S.DOWN if here < target else S.UP
        else:
            target = s["squad"].index(player) + 1
            if s["cursor"] != target:
                return self.move(s["cursor"], target)
        self.in_own, self.own_failed, self.presses = True, False, 0
        self._own_visit = (player, int(not in_pool))
        self._mark_pressed = self._mark_calls = 0
        self._mark_pending = False
        return self.act(S.KEY_T)

    @staticmethod
    def mark_reached(status, word, target):
        # [confirmed: F010 49B8] Element7 clear inherits; explicit0 protects zone.
        return not bool(status & 64) if target is None else bool(status & 64) and word == target

    def observe_mark_state(self, status):
        self._mark_status = status

    def observe_mark_entry(self, player, pane, key, row):
        if (self._own_visit != (player, pane) or player not in self.marking
                or not self._own_entered or self._mark_pending
                or self._mark_calls >= self._mark_pressed or pane != 1 or key != S.ENTER or row != 5):
            raise MatchError("original pre-match marking entry differs from requested row5")
        self._mark_pending = True

    def observe_mark_return(self, player, pane, key, row):
        if not self._mark_pending or self._own_visit != (player, pane) or key != S.ENTER or row != 5:
            raise MatchError("original pre-match marking return differs from requested row5")
        self._mark_pending = False
        self._mark_calls += 1

    def observe_mark_visit(self, player, status, word):
        if player in self.marking and (not self._own_returned or self._mark_pending
                or self._mark_calls != self._mark_pressed
                or not self.mark_reached(status, word, self.marking[player])):
            raise MatchError("original pre-match marking goal or call witness was not reached")

    def own_key(self, row, own_set, marking_word, team_set, can_mark):
        job = self.jobs[self.job]
        for e, v in job[2].items():
            has, value = bool(own_set & (1 << (e+3))), bool(own_set & (1 << (e-1)))
            if (v is None and has) or (v is not None and (not has or value != v)):
                return super().own_key(row, own_set, marking_word, team_set, can_mark)
        player = job[1]
        if player in self.marking and not self.mark_reached(self._mark_status, marking_word, self.marking[player]):
            if not can_mark:
                raise MatchError("original pre-match player has no marking row")
            if row != 5:
                return self.move(row, 5)
            self._mark_pressed += 1
            if self._mark_pressed > 13:
                raise MatchError("original pre-match marking goal was not reached")
            return self.act(S.ENTER)
        return self.act(S.ESC)

    def select_key(self, s):
        if self._position_visit is not None:
            if not self._position_observed:
                raise MatchError("original pre-match position input has no return witness")
            self._position_visit = None
            self._position_observed = False
            self._position_entered = False
            if self.jobs[self.job][2] == "club":
                self.done.append(self.jobs[self.job])
                self._next_job()
        if self.pending_check is not None:
            job = self.pending_check
            self.pending_check = None
            expected = self._expected_swap
            if (not self._swap_observed or expected is None
                    or Counter(s["squad"][:11]) != Counter(expected[0][:11])
                    or Counter(s["squad"][11:]) != Counter(expected[0][11:])
                    or s.get("pool", []) != expected[1]):
                raise MatchError(f"the original did not make the pre-match swap {job}")
            self._expected_swap = None
            self.done.append(job)
        if self.job == len(self.jobs):
            # [designed: T135] Keep T132's continued SELECT entry in the
            # squad pane, which each subsequent plan starts from. Use the
            # original toggle, never a private pane/cursor write.
            if self.pool_pane:
                self.pool_pane = False
                return self.act(S.LEFT)
            return self.act(S.ESC)
        job = self.jobs[self.job]
        if job[0] == "position":
            return self._position_key(s, job)
        if job[0] == "own":
            return self._own_select_key(s, job)
        if job[2] not in s["squad"] and job[2] in s.get("pool", ()):
            return self._pool_key(s, job)
        # Mark the nonzero incoming player first: DEA6 refuses to mark an empty outgoing slot.
        want = job[1] if self.sub_marked else job[2]
        if want not in s["squad"]:
            raise MatchError(f"pre-match player {want} is no longer in the squad")
        slot = s["squad"].index(want) + 1
        if s["cursor"] != slot:
            return self.move(s["cursor"], slot)
        self.sub_marked = not self.sub_marked
        if not self.sub_marked:
            self._expect_swap(s, job)
            self.pending_check = job
            self.job += 1
        return self.act(S.ENTER)

    def _pool_key(self, s, job):
        """[T128, F011, #709] The incoming is a made-pool word: T128's pool-to-squad case. Either
        toggle key flips the SELECT screen's pane outside a match (E6C7-E6D4, one press one flip);
        the pool-pane Enter asks DBFA before DEA6 marks, and DEA6's selected word sits at the list
        index scroll(+0x52) + cursor(+0x5E) - 2 of the manager. The squad-pane Enter completes the
        exchange (214B:007B swaps the word-list entries; the squad is sorted)."""
        if self.pool_pane == self.sub_marked:
            self.pool_pane = not self.pool_pane
            return self.act(S.LEFT)                     # the toggle key E009-r0001 pressed
        if not self.sub_marked:
            if job[2] not in s["pool"]:
                raise MatchError(f"pre-match pool player {job[2]} is no longer in the pool")
            at = s["pool_scroll"] + s["pool_cursor"]    # = the list index + 2 (T128's prepare)
            target = s["pool"].index(job[2]) + 2
            if at != target:
                self.moves += 1
                if self.moves > 2 * MAX_MOVES:         # the pool holds eighty entries (F011), not twenty
                    raise ScreenError(f"the pool cursor does not reach pool index {target - 2}")
                return self.act(S.DOWN if at < target else S.UP)
            self.sub_marked = True
            return self.act(S.ENTER)                    # marks the pool player (DBFA gates)
        want = job[1]
        if want not in s["squad"]:
            raise MatchError(f"pre-match player {want} is no longer in the squad")
        slot = s["squad"].index(want) + 1
        if s["cursor"] != slot:
            return self.move(s["cursor"], slot)
        self.sub_marked = False
        self._expect_swap(s, job)
        self.pending_check = job
        self.job += 1
        return self.act(S.ENTER)                        # completes the exchange


class RouteMatch(Match):
    """Match's guest and key service, with the route harness's pre-match choice and complete key log."""
    def __init__(self, *args, **kwargs):
        self.team_choices = []
        self.team_keys = []
        super().__init__(*args, **kwargs)

    def _team_menu_key(self, item):
        if self.st["menu_context"] == "pre_match" and self.side is not None and self._menu is None:
            squad = self._squad(self.opts["managed"])
            changes = choose_eleven(squad, self._player)
            self.team_choices.append({"country": self.opts["managed"], "before": squad, "swaps": changes})
            self._menu = PreMatchPlan(self.side, subs=changes)
        return super()._team_menu_key(item)

    def _on_readkey(self, replay):
        # 08DD consumes a pushed-back byte itself, so Match does not call _key_for for this read.
        if self.m.rd(PUSHED_BACK, 1):
            site = self.m.where(self.m.stack_word(2), self.m.stack_word(0))
            self.team_keys.append({"site": site, "key": self.m.rd(KEY, 1),
                                   "context": self.st["menu_context"], "source": "pushed-back"})
        return super()._on_readkey(replay)

    def _key_for(self, site):
        if site == SITE_SELECT and self.st["menu_context"] == "pre_match" and isinstance(self._menu, PreMatchPlan):
            scroll, cursor = self._pool_state()         # [T128] the pool pane's own state words
            key = self._menu.select_key({"cursor": self.m.rd(S.SELECT_CURSOR),
                                         "squad": self._squad(self.opts["managed"]),
                                         "pool": self._pool(), "pool_scroll": scroll, "pool_cursor": cursor})
        else:
            key = super()._key_for(site)
        if key is not None:
            self.team_keys.append({"site": site, "key": key, "context": self.st["menu_context"]})
        return key
