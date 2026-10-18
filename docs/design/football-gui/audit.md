# Audit and reference board

[designed: #182] Audit baseline: goal2 `650189cbc58b67bcd3d1d775feb8b53c1bcf2c89`.
This document distinguishes code observations, accepted evidence and proposed design.
Line anchors below describe this pin; implementers must re-read the current head.

## Existing desktop flows

[derived: baseline `goal2/desktop/window.py:17–86`, `model.py:19–72`]
The initial1050×780 window vertically stacks a title/country picker, new-mode
buttons, fixture/morale summary, standings button, squad/reserve splitter,
captain/draft buttons, eight tactics, save path/actions, play/cancel, halftime
controls, result and status. This makes competing actions visually equal and
shrinks the player area. The proposed shell groups those same actions by intent.

| Existing seam at baseline | Required continuity | Proposed location |
| --- | --- | --- |
| [derived] `window.py:88–132`: display model, saved active draft, country preview | Preview must use its own generated roster/header/tactics/result/pool. Returning restores the active draft. New mode or Resume explicitly replaces active game. | Country browser and overview; persistent **Preview** / **Active game** text |
| [derived] `window.py:133–178,201–204`, `model.py:106–128,143–156`: full integer IDs, eleven/captain/tactics, eligibility/morale | Exactly eleven available players; captain belongs to XI; edits stay private until confirmation; unavailable starter removable; no truncating IDs above255. | Squad/tactics with an explicit draft action bar |
| [derived] `window.py:238–264`, `model.py:59–72`: eighty reserves, filter, exchange | Filter is read-only; existing exchange window/reason is authoritative; exchange discards draft and repairs confirmed XI/captain. Standalone has no pool. | National pool view, selected outgoing/incoming summary |
| [derived] `model.py:158–179`: atomic save/validated resume | Confirmed state only; invalid save/resume retains prior good game and file; no match-pending save. | Save/resume view; visible path and inline feedback |
| [derived] `window.py:206–235`, `jobs.py:16–142`: one process, busy gating, candidate validation/cancel | UI thread owns publication; no navigation-triggered worker, blocking animation or duplicate match; stale completion cannot publish. | Match progress view with always-visible Cancel |
| [derived] `window.py:266–288`: quick campaign halftime | Private pending XI, available bench, no re-entry, explicit Continue; cancel preserves committed game/save. | Match decision panel, same draft hierarchy |
| [derived] `standings.py`, `model.py:130–141`, `result_text:74–104` | Keep source A/B fixture order and existing standings keys; distinguish quick result, original result and competition stage scores/penalties. | Fixtures/results view and existing standings dialog |

[derived: baseline `docs/desktop-management.md`, `docs/desktop-ui-roadmap.md`,
`docs/tasks/T66.md`] The application supports national management, not club
finances/transfers/training, live tactical formations or a club career. Use the
real fields already exposed: country, position group, ability, energy, confidence,
eligibility, morale, fixtures, XI/captain, eight tactics, pool, result and save.
The twelve original skill bars and original player biography are reference cues,
not authorization to add new data adapters in this redesign.

[designed] T66 (#136) is a concurrent integration dependency, not established at
this audit pin. Its separate Pygame window is limited to original-friendly events,
commentary, score and result boards. Do not present competitive watching, pitch
animation, in-play editing or mid-match saves as available. [T80](../../tasks/T80.md) owns asynchronous competitive Play; T50 owns qualifying
progression after that seam. Consume their accepted capability interfaces before
offering new competitive actions; neither task authorizes competitive watching.

## Original GOAL reference board — private sources, no copied assets

[confirmed: accepted archaeology kit pin
`424d5998076da1e4efc399c2715689ddb44d3e1a` (PR255); goal2 acceptance T51a PR172
`281d7912ac35104dd0c1650a4f431054e2967e73`; see `PROVENANCE.md`]
The source catalogue is in **goal2-archaeology**, not this repository:
[`docs/screens.md`](https://github.com/diegoami/goal2-archaeology/blob/424d5998076da1e4efc399c2715689ddb44d3e1a/docs/screens.md),
[`static/screens/kinds.tsv`](https://github.com/diegoami/goal2-archaeology/blob/424d5998076da1e4efc399c2715689ddb44d3e1a/static/screens/kinds.tsv),
and [`catalogue.tsv`](https://github.com/diegoami/goal2-archaeology/blob/424d5998076da1e4efc399c2715689ddb44d3e1a/static/screens/catalogue.tsv).
Catalogue `screen` hints and multi-key `run` bursts are different evidence; a burst
is not proof that a single key caused a transition. Private links require access.

| Study panel (source at accepted pin) | Observation / confidence | Retain / modernize |
| --- | --- | --- |
| [confirmed] E015-r0007 state16, `static/screens/png/E015-r0007-state0016.png` | Inspected private rendered manager menu: black background, thin colored frames, cyan actions, roster at right, named country and next opponent. Catalogue kind `manager-menu`. | [designed] Country/next-opponent anchors and bounded panels; replace tiny glyphs and scattered function-key hints with readable headings, visible navigation and focus. |
| [confirmed] E015-r0007 state76, `static/screens/png/E015-r0007-state0076.png` | Inspected private player/substitution screen: named player, colored skill bars, role/tactics detail, roster split and substitution prompt. Catalogue has several substitution kinds; no stronger key claim from the image alone. | [designed] Selected-player detail, readable attribute bars and XI/bench split; retain values/text as well as color; do not copy original font, glyphs or screen bitmap. |
| [confirmed] Catalogue `country-select`, `team-tactics`, `captain-select` | Named browse/select/captain/tactics tasks are evidenced; F010 records tactics display order5,6,7,1,2,3,4,8, F011 squad20/reserves80 in separate views. | [designed] Keep purposeful screens, obvious national identity and captain badge; modernize browse/preview feedback and group management drafts. |
| [confirmed] Catalogue `fixtures-watch`, `fixtures-auto`, `match-commentary`, `match-summary`; kit `screens.py` at same pin, F014 | Separate match routes and full-time information exist in original evidence. This is not proof of current GUI competitive/watch coverage. | [designed] Scoreboard, ordered commentary and explicit result provenance; no replay/animation promise. |

[derived: `PROVENANCE.md`] Earlier accepted data/player/tactics basis is `8760df9`
(F002/F007/F010/F011; `players.py` pin); condition/morale basis is
`0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb` (F018/F019/F020). F010's current
upstream file contains labels beyond the accepted Qt conventions: this planning
study records baseline `window.TACTICS` strings/masks without changing runtime.
T76 depends on #164 and consumes its corrected accepted label source; it must
not freeze inherited wrong labels or change masks under a visual redesign. Proposed bars
show raw ability/energy/confidence values; they must not invent percentages or
normalize to100 without a proven domain.

## Modern primary references — link board, no downloaded art

[confirmed: official sources visited 2026-10-18]
[FM26 interface study](https://www.footballmanager.com/fm26/features/fm26s-reimagined-user-interface)
shows an overview-to-detail hierarchy and grouped navigation; its Portal Example,
Navbar Snip and Calendar Example are the reference panels. The relevant lesson is
that key decisions should be legible before opening details. [designed] Adopt
that principle through five stable destinations, not FM's copied tile/card art,
fonts, badge designs, mail/news systems or interaction wording.

[confirmed: official source visited 2026-10-18]
[EA SPORTS FC26 career study](https://www.ea.com/games/ea-sports-fc/fc-26/news/pitch-notes-fc26-career-mode-deep-dive)
is a primary visual reference for team-centered career/match presentation.
[designed] Use the general importance of team identity and match emphasis, not
its branded graphics, commercial club badges, licensed player portraits, gameplay
features or art assets. The prototype is entirely original HTML/CSS/SVG geometry;
these references are inspiration rather than engine evidence or acceptance.
