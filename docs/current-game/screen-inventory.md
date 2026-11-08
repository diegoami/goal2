# Every screen the build has today

[designed: T176] One row per captured screen: what it shows, the keys **it prints itself**, and the
original screen it stands for ([the original's inventory](../original-game/screen-inventory.md)).
Keys are quoted from the screen's own hint line, which is the build's own statement of them; where a
key is in the code but not printed, the row says so. "Differs" records a difference from the
original without judging it.

The route column is the [README](README.md)'s: **boot** is the route a player gets, **core** the same
window resumed from a mid-career savestate, **template** goal2's own Python game, **first start**
the import dialog.

## First start

| Screen | Shows | Keys | Original | Differs |
| --- | --- | --- | --- | --- |
| [import-data-folder](images/import-data-folder.png) | the files goal2 needs, where it will put them, *Choose folder…* and *Quit* | buttons only; no key is printed | none — goal2 adds it (T153) | the original ships with its own files; the rebuild cannot |
| [import-data-refused](images/import-data-refused.png) | the same dialog with the reason a folder was refused, in red, above the buttons | as above | `file-not-found-prompt` is the nearest | the original's prompt is `try again? (Y/N)`; here the dialog simply stays open |

## Launch: start or resume

The same window on both routes; the new-career pages differ because the core route starts the
original's own new game.

| Screen | Route | Shows | Keys | Original | Differs |
| --- | --- | --- | --- | --- | --- |
| [boot-launch-start](images/boot-launch-start.png) | boot | *SAVED CAREER* (here `NO SAVED CAREER`, with the reason) and *NEW GAME*: *New career >*, a path field, *Open another save* | "Arrows: choose / Enter: accept / Esc: back / Existing saves stay yours" | `title-load-prompt`, load name, `file-not-found-prompt` | the original asks Y/N then for a file name; here both are on one page, and a save is a path |
| [template-launch-start](images/template-launch-start.png) | template | the same with a save present: country, manager, campaign, next and following fixture, checkpoint, team; *RESUME BULGARIA* | as above | as above | the summary has no original counterpart |
| [boot-launch-country](images/boot-launch-country.png) | boot | the 128 countries with world and continent rank; the card: team, status, skill, ranking now/top, formation with role codes, strips, team tactics, player defaults, team skills, performance, characteristics; *Start year*; *SPACE: PLAYERS* | "Arrows: country / Enter: review / Esc: back" | `country-select` | the original's **Ins** (world/continental swap) has no control here; the start year is a drop-down the original does not ask for; undecoded values say "not decoded yet (G05)" |
| [template-launch-country](images/template-launch-country.png) | template | the same list; the card is the Python game's, with fewer decoded values | as above | `country-select` | as above |
| [template-launch-players](images/template-launch-players.png) | template | that country's twenty with role codes, and the selected player's complete card | Space from the country list | the country's player card | on the boot route this page cannot be reached (see *Not captured*) |
| [boot-launch-review](images/boot-launch-review.png) | boot | country, manager line, campaign, what happens first, what is saved; the **name field** (initial and surname, 14 characters); *Start career*; the substitutions rule | "Type the name / Enter: start / Esc: back to countries" | `country-select-name-entry` | the original types the name over the country card; here it is a page of its own, after the card |
| [template-launch-review](images/template-launch-review.png) | template | the same page for the Python game | as above | as above | as above |
| [boot-bulletin-1](images/boot-bulletin-1.png), [boot-bulletin-2](images/boot-bulletin-2.png) | boot | `BULLETIN n OF m` and the original's three stories under their mastheads: *D A I L Y  R A G*, *THE SOCCER BULLETIN*, *✳ Sporting Times ✳* | "Enter: next page" | `bulletin` | the words and capitals are the original's; the newspaper itself is not: no paper colour, no greeked columns, no photo block, no page rules |

## The main window on the core (boot and core routes)

Every page has the same frame: a **top bar** (GOAL2, the country, manager/year/stage, the next
fixture), a **side bar** (the five destinations, `Ctrl+1`–`Ctrl+5`, and *SHOW MATCH (F8)*), the page,
and a magenta **status line** that reads "The original game runs as the core; its screens are read
from its memory."

| Screen | Shows | Keys | Original | Differs |
| --- | --- | --- | --- | --- |
| [boot-country](images/boot-country.png), [core-country](images/core-country.png) | *NAME / RATING*, *TEAM* with world and Europe rank, *NEXT OPPONENTS* with theirs and the fixture's kind, the *MANAGERS* board 1–6, the original's six routes as buttons (*team info*, *fixture list*, *tournament*, *history*, *select squad*, **PLAY NEXT GAME >**), and the squad strip: eleven, a rule, nine, each with initial, surname and the role code at the right | buttons; `Ctrl+1`–`5`; F8 | `manager-menu` | the original's hub is one screen of boxes with a cursor and `Use ↑↓ / Hit ◄┘` hints; here the routes are buttons and the destinations are a side bar. *PLAY NEXT GAME* is yellow; the original's *play next game* is one option among six |
| [boot-country-coreHistoryView](images/boot-country-coreHistoryView.png), [core-country-coreHistoryView](images/core-country-coreHistoryView.png) | *STATISTICS* (consecutive wins/defeats, games without a win/defeat, home/away/all, now/top), *SUCCESSES* (WC/CH, 1st–4th), *RESULTS*, *TOP SCORERS*, *TOP CAPS*, *RECORDS* | *< Desk (Esc)* | the original's history screens | the panels are the original's; the frames and headings are the build's |
| [boot-team](images/boot-team.png), [core-team](images/core-team.png) | the selected player's card: name, role code, age, caps, goals, height, foot, readiness, national and club position, cards, performance, the twelve skill bars, the five characteristics with their word, the tactics block; and *Team tactics >*, *Own tactics (T) >*, *Reposition (R)*, *Club position (C)*, a name field, *Rename (F2)* | R, C, T, F2 are printed on the buttons | the squad/pool card and `squad-substitution-tactic` | the bars are blocks of cells, as the original's are; the original's screen also carries the hint lines and the pool toggle (←→), which are not here |
| [boot-team-teamTacticsView](images/boot-team-teamTacticsView.png), [core-team-teamTacticsView](images/core-team-teamTacticsView.png) | *TEAM TACTICS*: the country card with formation, team skills, performance and characteristics beside the eight tactics (defence system, protection, offside, positioning, possession, passing, tackling, marking) | "Enter or Space: change the selected tactic / Esc: back to team" | `team-tactics` | the original lists the eight in one column with its own frame; here they are a two-column grid in a box |
| [boot-team-teamOwnView](images/boot-team-teamOwnView.png), [core-team-teamOwnView](images/core-team-teamOwnView.png) | the selected player's own tactics: positioning, possession, passing, tackling, marking, with `P` marking a personal choice | "Enter: the team's tactic, his own (P) one way, his own the other way / Esc: the card" | `squad-substitution-tactic` | the original shows these beside the player's card; here the card is replaced by the list |
| [boot-pool](images/boot-pool.png), [core-pool](images/core-pool.png) | the selected pool player's card, the same shape as the Team card, and the pool list `POOL 1-21/80` with caps and the role code; *Squad / pool (←→)*, *Move player (Enter)*, *Compare >*, *Suggest* | "Enter marks a player; Enter on another moves him (squad ⇄ pool)", ←→ | the pool card and its two-Enter exchange | the keys are the original's ←→ and two Enters; *Suggest* is the original's **Ins** (the assistant's twenty) as a button |
| [boot-pool-compare](images/boot-pool-compare.png), [core-pool-compare](images/core-pool-compare.png) | the compare and exchange view: *TEAM PLAYER* drop-down, two cards, *Exchange these players* | "Choose both players; Exchange confirms the change." | the original's two-Enter exchange | the original exchanges with two Enters on one list; here it is a drop-down, two panels and a button. **The capture opened this view with nothing chosen, so both panels read "Choose a player to compare"** |
| [boot-fixtures](images/boot-fixtures.png), [core-fixtures](images/core-fixtures.png) | *FIXTURES AND RESULTS*: every fixture of the round as `side v side  kind`, with `√` on the player's own; the count and the scroll keys | "640 fixtures from number 1361; Up/Down/PgUp/PgDn scroll; √ marks your fixtures" | `fixtures-watch`, `fixtures-auto` | the original's `√` means *marked to watch* and Enter changes it; here `√` means *yours* and Enter does nothing. The original's dash leaders and its top-right hint are not here |
| [boot-fixtures-coreTournamentView](images/boot-fixtures-coreTournamentView.png), [core-fixtures-coreTournamentView](images/core-fixtures-coreTournamentView.png) | *EUROPE / QUALIFYING*: the group table (P W D L F A T) and the group's fixtures with `√` | "Up/Down: group" | the tournament group table | the original's table is its own screen with its own frame; the columns are the original's |
| [boot-save](images/boot-save.png), [core-save](images/core-save.png) | *Core save*: the path, *Save (F7)*, and the command line that resumes it | F7 | `save-game-name-entry`, `save-game-prompt`, `quit-confirm` | the original asks for a **name** and asks *save?* before quitting; here it is a path field and a button, and the page prints a shell command |

## The round, on the core

Views of *Fixtures & match* while a round is played. Each is reached by playing, never from the
side bar.

| Screen | Shows | Keys | Original | Differs |
| --- | --- | --- | --- | --- |
| [boot-round-before](images/boot-round-before.png) | the destination before the round starts | — | `manager-menu` before *play next game* | — |
| [boot-round-01-captain](images/boot-round-01-captain.png) | *THE ROUND'S RESULTS*: the other fixtures of the round and their scores, in the original's own page text, in a bordered board; *Next > (Enter)* | Enter | `round-playing`, `round-results` | the original's pages fill the screen; here they are a board inside the page, with the rest of the page empty |
| [boot-round-02-captain](images/boot-round-02-captain.png) | *CAPTAIN*: the eleven with role codes, the suggested captain, and four actions: *Select (Enter)*, *Computer (C)*, *Kick off and watch (Enter)*, *Kick off, quick result (Q)*, *Players: select your team >* | Enter, C, Q | `captain-select` | the original's captain card is one card with Up/Down and Enter, and the watch decision was made earlier; here the same screen carries the watch/quick choice (T155, #523) |
| [boot-round-live-window](images/boot-round-live-window.png) | **while a watched match runs**: two lines of magenta text and an otherwise empty page | — | `match-live` | the original plays the match on this screen; here the match is in a second window and the main window has nothing to show |
| [boot-round-taker](images/boot-round-taker.png) | *CORNER TAKER / BULGARIA*: the eleven and the selected player's whole card | "Up/Down select / Enter choose / C original choice / Esc keep / Space view pitch" | the original's taker cards | the keys are the original's. The roster heading is **clipped** ("FIRST ELEVEN 11 / XI 11 / BE") |
| [boot-round-03-half-time](images/boot-round-03-half-time.png) | *HALF TIME NORWAY 1 - 0 BULGARIA*, substitutions left, the selected player's card, *R - next position*, *C - club position*, *MAKE SUBSTITUTIONS NOW*, *Start second half* | "HALF TIME — MAKE SUBSTITUTIONS NOW. Start second half when ready." and "Enter - take off this player" | `match-menu-halftime`, `squad-substitution-take-off`/`put-on` | the original shows the match menu with the score and opens the bench from it; here the bench is the half-time screen |
| [boot-round-04-menu](images/boot-round-04-menu.png) | *RESULT AND SUMMARY*: `FULL TIME`, the score, the scorers with minutes | Enter | `match-menu-fulltime`, `match-summary-save-prompt` | the original's full-time board carries corners, free kicks, penalties, shots, on target, saves, fouls, bookings, red cards, possession and territory, and MAN OF THE MATCH; this page shows the score and the scorers |
| [boot-round-05-menu](images/boot-round-05-menu.png) | the bulletin after the round, the same three panels as at the start | Enter | `bulletin` | as the Launch bulletins |
| [boot-round-after](images/boot-round-after.png) | the Country page again, with the next opponent updated | — | `manager-menu` | — |
| [boot-fixtures-coreRoundView](images/boot-fixtures-coreRoundView.png), [core-fixtures-coreRoundView](images/core-fixtures-coreRoundView.png) | the round view when no round is running | — | — | — |

The pitch itself is [its own chapter](match.md).

## The main window on the Python game (`--template`)

A different window (`goal2/desktop/window.py`), with a retractable top and side bar and a footer of
management actions.

| Screen | Shows | Keys | Original | Differs |
| --- | --- | --- | --- | --- |
| [window-country](images/window-country.png) | *YOUR COUNTRY*, *NEXT OPPONENT*, *YOUR CAMPAIGN*, *LAST RESULT*, the ready count and captain, seven buttons (*Prepare match*, *Select squad*, *Pool*, *Fixture list*, *Country card >*, *Manager name*, *Other games >*), and the squad strip with `+`/`-` for the eleven and the bench | `Ctrl+1`–`5`, F11 | `manager-menu` | the panels carry campaign text the original has elsewhere; the strip marks selection with `+`/`-`, which the original does not have |
| [window-country-countryCardView](images/window-country-countryCardView.png) | the country card view — **empty in this capture**: it was opened without choosing a country first | *< Desk (Esc)* | `country-select`'s card | the empty state is the capture's doing, not a defect |
| [window-country-countryGames](images/window-country-countryGames.png) | the other games of the round | — | `round-results` | — |
| [window-team](images/window-team.png) | the same player card as the core route, with *Pool / Compare >*, *Team tactics >*, *Rename (F2)*, and a draft footer: "Unconfirmed draft · XI 11/11", *Discard draft*, *Confirm management* | F2 | the squad card | **the draft/confirm step has no original counterpart**: the original's changes take effect as they are made |
| [window-team-teamTacticsView](images/window-team-teamTacticsView.png) | the eight team tactics for the Python game | — | `team-tactics` | — |
| [window-pool](images/window-pool.png) | a table of the 80 reserves: ID, Player, Role, Position, Energy, Confidence, Availability, with a name search and a position filter, and *Exchange selected squad player and reserve* | — | the pool card | **the least like the original of all the screens**: a spreadsheet of numbered rows, with internal ids and an availability policy note, where the original shows one player's card at a time |
| [window-pool-poolCardsView](images/window-pool-poolCardsView.png) | the pool's cards view | — | the pool card | — |
| [window-fixtures](images/window-fixtures.png) | the next match: both lineups with role codes and formations, and a *PLAY* panel — *Play quick friendly*, *Watch original friendly*, six speed buttons, *Fixture list >*, *Half time >* | — | `match-menu` | the original's match menu is the two sides mirrored with connector lines and a middle column; the speeds are chosen here instead of with ←→ during play, and the panel explains itself in prose |
| [window-fixtures-fixtureListView](images/window-fixtures-fixtureListView.png) | the fixture list for the Python game | — | `fixtures-watch` | — |
| [window-fixtures-matchResultView](images/window-fixtures-matchResultView.png) | the result after a quick friendly | — | `match-summary` | — |
| [window-fixtures-halfTimeView](images/window-fixtures-halfTimeView.png) | the half-time decision | — | `match-menu-halftime` | — |
| [window-fixtures-benchView](images/window-fixtures-benchView.png) | the bench | — | `squad-substitution-*` | — |
| [window-save](images/window-save.png) | *Save file* path, *Save*, *Save as…*, *Resume* | `Ctrl+S` | `save-game-name-entry` | a path, not a name |
| [window-bars-retracted](images/window-bars-retracted.png) | the same page with both bars retracted to `[Menu >]` and `[v Top]` (F11) | F11 | — | goal2 adds it; the original has no bars to retract |
| [window-small](images/window-small.png) | the Save page at 900×640: the whole page scaled, same layout | — | — | T101: one fixed page, scaled, never re-flowed |

## Not captured

Honest gaps in this manual. Each is a screen the build has, or may have, that this run did not
reach; none is described from memory.

| Screen | Why |
| --- | --- |
| the country's players on the boot route (`Space` from the country list) | the run raised `AttributeError: 'NoneType' object has no attribute 'state'`: that page reads the Python browser, which the core route does not build. Whether the button is reachable by a player on this route is **unverified** |
| a goal, an injury, a card, a replay offer, a shoot-out, extra time | the captured round had none of them |
| the end of a stage, the finals draw, the year's end, elimination | the capture plays one round of one year |
| two to six managers | the build creates one; the *MANAGERS* board shows 2–6 empty |
| every screen on Windows | the capture runs on Linux, offscreen |
| the Launch bulletin page on the `--template` route | the page is built on both routes but filled only by the core route's new game, so there is nothing to show |
