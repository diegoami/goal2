# One-letter role codes

[designed: owner, 2026-10-21] Wherever a player's role is shown, on the pitch, in the squad and
pool lists and on the player card, the game shows a **one-letter code**, as the original does,
in the spirit of One Nil. The accepted screens of #266 ([screens/](../screens/)) print
two-letter roles (GK, RB, MF, FW…). The ten sheets in this folder are the same illustrations
redrawn with the codes, and they supersede those screens for role display. The accepted screens
stay pinned and unchanged.

[confirmed: goal2-archaeology F002 R011 at `a737716a`; screenshots
[m244-squad](../../original-game/images/m244-squad.png) and
[m244-position-next](../../original-game/images/m244-position-next.png)] The original stores
a position value 0..13 in each player's field +6 and prints it through a 14-byte table at
`DS:69A8`: `G S C B B D 80 M M F W W 9B 24`. In code page 437, 80 is Ç, 9B is ¢ and 24 is $. Its
squad strip colours each code by line: green goalkeeper, red defence, cyan midfield, yellow
attack.

| Value | Position | Original | Shown |
| --- | --- | --- | --- |
| 0 | Goalkeeper | G | G |
| 1 | Sweeper | S | S |
| 2 | Centre back | C | C |
| 3 | Left back | B | **b** |
| 4 | Right back | B | B |
| 5 | Defensive midfield | D | D |
| 6 | Central midfield | Ç | Ç |
| 7 | Left midfield | M | **m** |
| 8 | Right midfield | M | M |
| 9 | Forward midfield | F | F (not in the owner's list; owner to confirm) |
| 10 | Left winger | W | **w** |
| 11 | Right winger | W | W |
| 12 | Centre forward | ¢ | ¢ |
| 13 | Striker | $ | $ |

[designed: owner, 2026-10-21] Lower case marks the left-hand back, midfielder and winger. The
original prints both sides in one letter. [designed] The codes given to the fictional players
of these sheets are in [codes.json](codes.json), consistent with each player's two-letter role
and the 4-4-2 spots (right to left: B C C b, M Ç Ç m, $ ¢). Regenerate and check with
`python3 docs/vision-266/render.py --role-codes [--check]` (Pillow and Inkscape). Without
`--role-codes` the renderer still reproduces the accepted screens byte for byte.

[designed] Noted, not changed here: on the pitch (06, 15) the accepted geometry puts Holland's
right back at the top while Holland attacks to the right, which is its left side. The letters make
this visible; the layout is kept as accepted.
