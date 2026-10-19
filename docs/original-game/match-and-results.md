# A round, watched match, interventions and results

A match can be processed quickly or watched. The original sometimes asks whether to watch a selected fixture, then puts the managed side's choices on a match menu before the pitch. The prompt's Y/N and context are visible; a marked other-country fixture follows a shorter branch without the managed captain screen. [confirmed: E031 C18, C35–C38, C68–C68b]

![Watch-match question over the pre-match screen](images/match-watch-prompt.png)

*Watch question, `E015-r0007 state 28`. Its menu still shows teams, lineups and match actions underneath. E031 recorded Y entering watch; the reviewed prompt finding says this particular question has no timeout. [confirmed: E015-r0007 state 28; E031 C35; reviewed F030]*

![Pre-match menu with lineups and team actions](images/match-menu.png)

*Greece versus Hungary example, `E015-r0007 state 30`. Both formations and eleven-player strips remain visible while the cursor moves among team tactics, players, tournament, match stats and play; Ins toggles automatic action replay, with the current setting named at bottom. This is the place to compare sides and decide whether to change management before kick-off. [confirmed: E015-r0007 state 30; E031 C36–C37]*

For a managed watched match, **play** leads to captain selection; Enter accepts the highlighted player, or Up/Down chooses another before Enter. A quick result bypasses the watched pitch and its interventions; E031's Holland run used quick rounds for most fixtures while retaining watched examples. The computer's highlighted captain choice is timed according to reviewed F030. [confirmed: E031 C38–C38b, C35, C63; reviewed F030]

![Original captain card](images/captain-select.png)

*Captain select, `E015-r0007 state 63`. The player card and opponent/score context stay on screen while the selection is made. [confirmed: E015-r0007 state 63]*

## Pitch, speed and commentary

![Original live pitch at the opening of a friendly](images/match-live.png)

*Live pitch, `E015-r0007 state 31`. The header has match type, sides, score and event text; colored marks, goals and a ball are shown on the pitch. The bottom line prints display, speed, result, commentary and bench key hints. The picture represents a watched other-country game, so do not infer managed-team tactics from it. [confirmed: E015-r0007 state 31; E031 C39–C39c]*

E031 observed **Left** reducing speed by one `»` marker, **Up/Down** changing the display marks, **Space** opening commentary, and **R** moving to the quick result. The displayed F9 suffix and exact meaning of every pitch glyph remain unverified. Speed here is an original-game control, distinct from the remaster's new playback-rate design tracked in #243. [confirmed: E031 C39–C39c, C08; E015-r0007 state 31; evidence gap: F9 and glyph legend]

![Commentary view beside the pitch](images/match-commentary.png)

*Commentary view, `E015-r0007 state 67`. A scroll of event sentences appears beside the pitch while score/time and the bottom control legend remain. A manager can interpret the score in the context of chances and actions. [confirmed: E015-r0007 state 67; E031 C39c]*

## Conditional moments

After a goal, the original may ask to show an action replay and then whether to save the goal. With automatic replay switched off at the match menu, those questions do not appear according to the reviewed prompt finding. Set-piece taker prompts for corner and goal kick allow a selected player or C for computer choice; their default timeout behavior is in F030, while E031 captured each prompt text. These overlays require their own images before coverage is complete. [confirmed: E031 C37, C42–C43b; reviewed F030; evidence gap: replay/taker prompt screenshots]

![An injury reported during live play](images/injury-event.png)

*Greece versus Hungary live event, `E015-r0007 state 42`: the header reports “Kovacs INJURED” and “Fischer on for Kovacs” while the pitch and score remain visible. This is an observed injury and replacement for the side in this match; it does not prove the managed-team substitution path. [confirmed: E015-r0007 state 42]*

A rival substitution can produce a notice; a managed player's injury can produce an injury notice followed by “SUBSTITUTION OPPORTUNITY”. E031 also observed an injured player left on during a quick continuation repeatedly triggering the notice until the manager removed him. The case of no substitutions remaining was not seen and must not be invented. [confirmed: E031 C44–C46b, C71–C71b; evidence gap: no-substitution case]

## Half-time and bench

![Original halftime match menu](images/match-menu-halftime.png)

*Half-time menu, `E015-r0007 state 44`; the clock is 45 and match context remains. The bench is reached through **players**, and **play** starts the next half after management. E031 saw Enter or Space at the half-time board lead to the menu. [confirmed: E015-r0007 state 44; E031 C40–C40c]*

![Starter side of a substitution](images/squad-substitution-take-off.png)

*Take-off prompt, `E015-r0007 state 76`. The card still shows the player's skills/condition; the bench overlay states how many substitutions remain and what Enter will select. This supports a condition-based replacement decision. [confirmed: E015-r0007 state 76]*

![Bench side of a substitution](images/squad-substitution-put-on.png)

*Put-on prompt, `E015-r0007 state 82`. The two prompts are materially different states of one exchange. E031 recorded the two Enters working in either order and verified the substitute persisted at the next menu. [confirmed: E015-r0007 state 82; E031 C41d–C41k]*

The original manual/E031 evidence gives five substitutions in a friendly and two in a competition match. The right-side list, remaining count and each player's status support the choice. Esc once can leave the roster screen unchanged and a second Esc return to the match menu in the observed path; treat this as observed behavior, not a universal cancel guarantee for every intermediate state. [confirmed: E031 C41–C41j; original GOAL.HLP]

![Illegal substitution overlay](images/squad-substitution-illegal.png)

*Illegal-substitution response, `E015-r0007 state 176`. The blocked attempt is visibly rejected rather than silently applied. The exact predicate needs the adjacent input/state evidence before being stated as a rule. [confirmed: E015-r0007 state 176; evidence gap: precise predicate]*

## Full time, extra time and penalties

![Full-time match menu](images/match-menu-fulltime.png)

*Full-time menu, `E015-r0007 state 50`, where result context and match actions remain. In knockout play, E031 instead observed an “EXTRA TIME” menu with **play** when level after regulation; extra time also has its own half-time. The length of that extra-time half was not established by the E031 guide. [confirmed: E015-r0007 state 50; E031 C47–C47b; evidence gap: extra-time half length]*

![Original World Cup penalty shoot-out start](images/e031-shootout-start.png)

*Belgium 2–2 Holland, last sixteen, `E031 g1 step 3874`; published savestate SHA-256 `3ea57029282b849fd3114a995178f35e48c420c768f0702b9d3b7d48600dc1fc` and PNG hash are in [image provenance](image-provenance.tsv). The screen itself says “penalty shoot out PRESS ANY KEY”; it is the transition before choosing the order, not an invented order UI. [confirmed: E031 `out/states.tsv`, g1 step 3874; E031 C48]*

After this prompt, the managed team orders its takers using Up/Down and Enter; Esc undoes an order choice. E031 logged numbered picks, individual kick commentary and a sixth-kick continuation after five each were level. The other side's order was not seen. The order picker and scored-kick states need dedicated authentic captures before image coverage is complete. [confirmed: E031 C48b–C49d; evidence gap: order and kick images]

## Statistics and round exit

![Original match statistics and save-summary question](images/match-summary-save-prompt.png)

*Match statistics with a conditional summary-save prompt, `E015-r0007 state 51`. The screen compares the two sides' corners, penalties, shots, fouls, red/yellow cards, possession and territory and lists scorers. The prompt offers a save name; reviewed F030 says it occurs after a watched match and times out to No. [confirmed: E015-r0007 state 51; E031 C51–C51b; reviewed F030]*

![Saved match summary view](images/match-summary.png)

*Summary view, `E015-r0007 state 207`. E031 used F4 at the hub to load a match summary, then **match stats** to inspect its board. The specific screen shown here is one retained state; loading other summaries could change the values. [confirmed: E015-r0007 state 207; E031 C24–C24b]*

![Original round results](images/round-results.png)

*Round results, `E015-r0007 state 52`. After acknowledging results/bulletins, the manager returns to the hub to prepare for another fixture or save. The screenshot does not establish the number of intermediate screens for every competition branch. [confirmed: E015-r0007 state 52; E031 C35, C52–C55]*
