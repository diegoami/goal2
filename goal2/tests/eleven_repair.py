"""[designed: #698] One repair policy for an eleven the original refuses, from either menu.

The policy is T111's (test_core_continuation_t111.fix_eleven): the first eleven player whose
card the menu does not call fit goes out, the last same-line bench player it does call fit
comes in — the original decides legality; nothing is written to guest memory but the menu's
own keys. The menus differ in the card's fitness word and in the route that makes the swap:

- the match menu's card reads "selected" (1771:42A6) for the eleven and "on the bench"
  (1771:42AF) for the bench; the swap is prematch_swap before play, substitute in play;
- the manager menu's card reads "ready to play" (1771:4298); the swap is Driver.swap on the
  squad screen, whose mark check #697 fixed to the screen's own order.

T170e's private repair (test_season_1992_t170e.repair_eleven) moves here.
"""

ELEVEN, BENCH, READY = 0x42A6, 0x42AF, 0x4298      # [confirmed: views.player_card] the card's words


def _choice(state, fit_eleven, fit_bench):
    """(off, on) by T111's policy: first unfit eleven player out, last fit same-line bench player in."""
    from goal2.core import views
    m = views.Memory(state)
    rows = views.team(state)["squad"]
    cards = {r["player"]: views.player_card(state, r["player"]) for r in rows}
    off = next(r for r in rows if r["eleven"] and cards[r["player"]]["readiness"] != fit_eleven)
    on = next(r for r in reversed(rows) if not r["eleven"] and r["line"] == off["line"]
              and cards[r["player"]]["readiness"] == fit_bench)
    return off["player"], on["player"]


def fix_eleven(d, message):
    """The match menu's arm (T111's policy, behavior unchanged): the original decides legality."""
    from goal2.core import views
    m = views.Memory(d.wait.state)
    off, on = _choice(d.wait.state, m.code_str(0x1771, ELEVEN), m.code_str(0x1771, BENCH))
    if d.wait.kind == "match-menu" and not d.stoppage():
        d.prematch_swap(off, on)
    else:
        d.substitute(off, on)


def repair_eleven(d):
    """The manager menu's arm (T170e's policy): Driver.swap on the squad screen. Returns (off, on)."""
    from goal2.core import views
    m = views.Memory(d.wait.state)
    fit = m.code_str(0x1771, READY)
    off, on = _choice(d.wait.state, fit, fit)
    d.swap(off, on)
    rows = views.team(d.wait.state)["squad"]
    eleven = [r["player"] for r in rows if r["eleven"]]
    assert off not in eleven and on in eleven, (off, on, eleven)
    return off, on
