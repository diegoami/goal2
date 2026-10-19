# Classified screen inventory

The 29 rows below are the E015 classifier's current kinds. Each linked image is a full 640×400 screen. Game screens are embedded again beside their explanation in the relevant chapter. The table records one verified representative state per kind; materially different states and currently unclassified screens need their own images and descriptions. [confirmed: archaeology `static/screens/kinds.tsv`, `catalogue.tsv`, `tools/screens/render.py`]

| Kind | Original image | Source state | Current coverage |
| --- | --- | --- | --- |
| `dos-shell` | [Full screen](images/dos-shell.png) | E015-r0001 state 1 | See the interaction reference below |
| `title-load-prompt` | [Full screen](images/title-load-prompt.png) | E015-r0001 state 2 | Illustrated in [first session](first-session.md) and chapters |
| `title-player-count` | [Full screen](images/title-player-count.png) | E015-r0004 state 2 | Illustrated in [first session](first-session.md) and chapters |
| `country-select-name-entry` | [Full screen](images/country-select-name-entry.png) | E015-r0007 state 10 | Illustrated in [first session](first-session.md) and chapters |
| `country-select` | [Full screen](images/country-select.png) | E015-r0007 state 3 | Illustrated in [first session](first-session.md) and chapters |
| `bulletin` | [Full screen](images/bulletin.png) | E015-r0007 state 14 | Illustrated in [first session](first-session.md) and chapters |
| `manager-menu` | [Full screen](images/manager-menu.png) | E015-r0007 state 16 | Illustrated in [first session](first-session.md) and chapters |
| `fixtures-watch` | [Full screen](images/fixtures-watch.png) | E015-r0007 state 18 | See the interaction reference below |
| `fixtures-auto` | [Full screen](images/fixtures-auto.png) | E015-r0007 state 24 | See the interaction reference below |
| `round-playing` | [Full screen](images/round-playing.png) | E015-r0007 state 27 | See the interaction reference below |
| `round-results` | [Full screen](images/round-results.png) | E015-r0007 state 52 | See the interaction reference below |
| `match-watch-prompt` | [Full screen](images/match-watch-prompt.png) | E015-r0007 state 28 | See the interaction reference below |
| `match-menu-halftime` | [Full screen](images/match-menu-halftime.png) | E015-r0007 state 44 | See the interaction reference below |
| `match-menu-fulltime` | [Full screen](images/match-menu-fulltime.png) | E015-r0007 state 50 | See the interaction reference below |
| `match-menu` | [Full screen](images/match-menu.png) | E015-r0007 state 30 | Illustrated in [first session](first-session.md) and chapters |
| `match-live` | [Full screen](images/match-live.png) | E015-r0007 state 31 | Illustrated in [first session](first-session.md) and chapters |
| `match-commentary` | [Full screen](images/match-commentary.png) | E015-r0007 state 67 | See the interaction reference below |
| `match-summary-save-prompt` | [Full screen](images/match-summary-save-prompt.png) | E015-r0007 state 51 | See the interaction reference below |
| `match-summary` | [Full screen](images/match-summary.png) | E015-r0007 state 207 | See the interaction reference below |
| `squad-substitution-illegal` | [Full screen](images/squad-substitution-illegal.png) | E015-r0007 state 176 | See the interaction reference below |
| `squad-substitution-take-off` | [Full screen](images/squad-substitution-take-off.png) | E015-r0007 state 76 | See the interaction reference below |
| `squad-substitution-put-on` | [Full screen](images/squad-substitution-put-on.png) | E015-r0007 state 82 | See the interaction reference below |
| `squad-substitution-tactic` | [Full screen](images/squad-substitution-tactic.png) | E015-r0007 state 150 | See the interaction reference below |
| `team-tactics` | [Full screen](images/team-tactics.png) | E015-r0007 state 119 | See the interaction reference below |
| `captain-select` | [Full screen](images/captain-select.png) | E015-r0007 state 63 | See the interaction reference below |
| `save-game-name-entry` | [Full screen](images/save-game-name-entry.png) | E015-r0007 state 215 | See the interaction reference below |
| `quit-confirm` | [Full screen](images/quit-confirm.png) | E015-r0007 state 223 | See the interaction reference below |
| `save-game-prompt` | [Full screen](images/save-game-prompt.png) | E015-r0007 state 224 | See the interaction reference below |
| `file-not-found-prompt` | [Full screen](images/file-not-found-prompt.png) | E015-r0008 state 10 | See the interaction reference below |

The [provenance table](image-provenance.tsv) records both the full source savestate SHA-256 and the resulting PNG SHA-256. A savestate was matched to the source E015 manifest before rendering. The three earliest title/DOS states were fetched from the private E015 release; the others were found in retained local sittings. [confirmed: E015 manifests; renderer verification]


## Screen-by-screen interaction reference

The source-state column above anchors each row below. A control stated here comes from a printed hint or the cited single-step E031/M244 record; a blank in the record is called **unverified** rather than guessed. Chapter images are full-size Markdown embeds at the point of use. [confirmed: E015 catalogue; E031 claims; M244 logs]

| Screen or prompt | Entry, selection, exit and confirmation | Displayed information and decision |
| --- | --- | --- |
| `dos-shell` | Emulator command prompt before launching GOAL2; no game control. | Environment only. [confirmed: E015-r0001 state 1] |
| `title-load-prompt` | Initial game question; Y goes to save name/list, N starts new manager count. | Clear fork between resumed and new campaign. [confirmed: E031 C11–C12; M244-G1A-01 step 1] |
| `title-player-count` | New-game route; Left/Right changes 1–6, Enter accepts. | Number of local managers to be created. [confirmed: E031 C12; E015-r0004 state 2] |
| `country-select` | After manager count; arrows browse and Enter selects. Printed Ins hint swaps world/continental rankings. | Country identity, ranking/profile, displayed difficulty (`SIMPLE` here; `EASY TASK` on another E031 card) and current team context support choosing a side. [confirmed: E031 C13–C15; E015-r0007 state 3] |
| `country-select-name-entry` | After choosing country; type name, Enter accepts, Esc aborts the name entry. | Manager name over the selected country's card. [confirmed: E031 C15–C15b; E015-r0007 state 10] |
| `bulletin` | Automatic news after setup/round; printed any-key continuation. | Newspaper panels report group, player and campaign news. Later content varies; inspect before advancing. [confirmed: E031 C20, C56–C60, C66; E015-r0007 state 14] |
| `manager-menu` | Central hub after setup/load/round; arrows move highlighted action, Enter opens it; Space opened squad and T team tactics in G1A. F3/F4/F7/F10 are retrospective/save/quit shortcuts. | Managed country/ranking, next opponent, squad strip and action list orient the next decision. [confirmed: M244-G1A-02 steps 2–11; E031 C17–C26; E015-r0007 state 16] |
| `fixtures-watch`, `fixtures-auto` | Hub fixture list; Up/Down browse rows and Enter is context-dependent (watch flag on an other-country fixture; cancel/rearrange on own friendly). Esc returns. | Each row pairs sides and fixture type. A `√` means **currently marked to watch**; the top-right “watch match” or “auto result” hint names what Enter will do **next**. Thus classifier names describe hints, not present row state: `fixtures-watch` is unmarked and `fixtures-auto` is marked. G1A step 5 only moves selection. [confirmed: M244-G1A-03 steps 4–5; E031 C17–C18; E015-r0007 states 18,24] |
| `round-playing` | Entered by play-next-game; game advances results. Printed pause/speed hints are visible; precise effect of each untested key remains unverified. | Other scheduled fixtures and their scores show what the calendar is resolving. [confirmed: E031 C35; E015-r0007 state 27] |
| `round-results` | Appears after round processing; acknowledge to return toward hub, sometimes through bulletin/stage screens. | Scores for the whole round, not just the managed fixture. [confirmed: E031 C35,C52–C55; E015-r0007 state 52] |
| `match-watch-prompt` | Conditional Y/N before a marked fixture; Y enters watched route, N quick. No timeout for this question per F030. | Side names and pre-match menu remain visible below question. [confirmed: E031 C35–C37; reviewed F030; E015-r0007 state 28] |
| `match-menu` | Pre-match menu; Up/Down selects an action, Enter opens it; Ins toggles automatic action replay; play enters captain if managed. | Two formations, lineups, `location:`, opponent/score, tactics/players/tournament/stats/play choices; inspect both sides before kickoff. [confirmed: E031 C36–C38; E015-r0007 state 30] |
| `captain-select` | Managed watched-match play; Up/Down browses card, Enter accepts; timeout default documented in F030; `C-computer select` is also a printed hint, not independently tested here. | Player identity/card and captain choice. [confirmed: E031 C38–C38b; reviewed F030; E015-r0007 state 63] |
| `match-live` | Follows watch/play; Left reduces speed, Up/Down alter pitch marks, Space opens commentary, R requests quick continuation (which may still stop at half-time/extra-time/shoot-out). Printed `Esc,◄┘-bench` offers a direct bench route that was not single-step exercised. Half-time and goals interrupt automatically. | Match type, teams, score, clock/event text, ball/player marks and bottom key legend guide in-play decisions; F9 and exact mark glyphs unresolved. [confirmed: E031 C39–C40, C08; M244-G4C-07 steps 32–55; E015-r0007 state 31] |
| `match-commentary` | Space from pitch showed event text beside it; the screen prints `Esc-play` for returning, while that key transition was not separately exercised here. | Chronological chance/action text provides context for score changes. [confirmed: E031 C39c; E015-r0007 state 67] |
| `match-menu-halftime` | Automatic midpoint then Enter/Space reached match menu in observed path; players opens bench, play resumes. | Score and 45-minute context remain visible while making substitutions/tactical choices. [confirmed: E031 C40–C41; E015-r0007 state 44] |
| `squad-substitution-take-off`, `squad-substitution-put-on` | Players from match menu; Up/Down browses card, Enter chooses starter/bench in either order; second Enter completes exchange; Esc returned in observed path. | Candidate card, roster and substitutions-left count prevent blind changes. [confirmed: E031 C41–C41k; E015-r0007 states 76,82] |
| `squad-substitution-tactic` | T from selected match player; arrow/Enter options as the individual editor, Esc leaves. | Position, possession, passing, tackling and mark beside the player's card. [confirmed: E031 C33, C41; E015-r0007 state 150] |
| `squad-substitution-illegal` | Rejected substitution produces warning and prints `PRESS ANY KEY`; exact triggering predicate and acknowledgment transition are not single-step proven. | Explicit refusal; do not assume the lineup changed. [confirmed: E015-r0007 state 176; evidence gap] |
| `team-tactics` | T from hub in G1A; arrows select, Enter changes a visible line, Esc leaves in E031. | Defence system, protection, offside, positioning, possession, passing, tackling and marking with current options. [confirmed: M244-G1A-02 step 11; E031 C07; E015-r0007 state 119] |
| `match-menu-fulltime` | Appears after regulation watched match; level knockout may instead progress to extra-time play menu. | Final score, `location:` and actions before the stats/round exit; highlighted **exit** replaces pre-match **play**. [confirmed: E031 C47–C51; E015-r0007 state 50] |
| `match-summary-save-prompt` | Conditional after watched match; save question times out No in reviewed F030. | Final and half-time scores, scorers/minutes, MAN OF THE MATCH, corners, free kicks, penalties, shots/on target, saves, fouls, cards, possession and territory explain the result. [confirmed: E031 C51; reviewed F030; E015-r0007 state 51] |
| `match-summary` | Hub F4 loads retained match; match stats opens comparison board. | Past match result and the same comparative statistics for later review. [confirmed: E031 C24–C24b; E015-r0007 state 207] |
| `save-game-name-entry` | Hub F7; type or accept suggested name with Enter, Esc cancels. | Save filename over active manager context; no original GL enters this repo. [confirmed: E031 C25–C25c; reviewed F030; E015-r0007 state 215] |
| `quit-confirm`, `save-game-prompt` | Hub F10 opens quit question, then save question in observed E031 sequence; Y/N choice shown. | Two distinct decisions avoid confusing exit with saving. [confirmed: E031 C26–C26b; E015-r0007 states 223–224] |
| `file-not-found-prompt` | Invalid load name shows error and prints `try again? (Y/N)`; the actual retry/cancel transitions are not single-step proven. | Explicit reason resumed game cannot open. [confirmed: E015-r0008 state 10; evidence gap] |

Unclassified screens are equally part of the known interface: the [squad/pool cards and individual editor](squad-and-tactics.md), [tournament group table and history](competition-and-campaign.md), [load-name variant](startup-save-replay.md), and [extra time, shoot-out order and kicks](match-and-results.md) each have their own embedded original image and step/hash. The [coverage checklist](coverage.md) records known but uncaptured alternative states. [confirmed: M244-G1A-01/02/03; E031 g1 step 3874]
