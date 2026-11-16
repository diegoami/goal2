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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    def select_key(self, s):
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
            return self.act(S.ESC)
        job = self.jobs[self.job]
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
