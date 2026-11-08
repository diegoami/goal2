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
    def select_key(self, s):
        if self.pending_check is not None:
            job = self.pending_check
            self.pending_check = None
            if job[2] not in s["squad"][:11] or job[1] in s["squad"][:11]:
                raise MatchError(f"the original did not make the pre-match swap {job}")
            self.done.append(job)
        if self.job == len(self.jobs):
            return self.act(S.ESC)
        job = self.jobs[self.job]
        # Mark the nonzero incoming player first: DEA6 refuses to mark an empty outgoing slot.
        want = job[1] if self.sub_marked else job[2]
        if want not in s["squad"]:
            raise MatchError(f"pre-match player {want} is no longer in the squad")
        slot = s["squad"].index(want) + 1
        if s["cursor"] != slot:
            return self.move(s["cursor"], slot)
        self.sub_marked = not self.sub_marked
        if not self.sub_marked:
            self.pending_check = job
            self.job += 1
        return self.act(S.ENTER)


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
            key = self._menu.select_key({"cursor": self.m.rd(S.SELECT_CURSOR),
                                         "squad": self._squad(self.opts["managed"])})
        else:
            key = super()._key_for(site)
        if key is not None:
            self.team_keys.append({"site": site, "key": key, "context": self.st["menu_context"]})
        return key
