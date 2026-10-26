# Desktop country management

[designed: owner #148, T69] The primary desktop interface uses PySide6. Install
its optional dependency in a virtual environment (tested Python3.12/PySide6 6.12.0):

```sh
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install '.[desktop]'
python3 -m goal2.desktop --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --save .cache/desktop.g2save
```

[designed: T86; accepted vision #266 screen 01] That command opens the **Launch** window. Its
**Saved career** panel summarises the save at `--save`, as the validating loader reads it:
country, manager (the one-manager default; names arrive with #265), campaign year and stage,
next and following fixture, checkpoint and confirmed team. **Resume** validates the file again
and opens management. **Open another save** takes a path. A missing, corrupt or incompatible
save names the reason and offers **Retry** and **Load another**, with nothing else changed.
**New career** lists the 128 countries with world and continent rank. A private preview shows
the first fixture and the twenty players, and names the profile categories this build does not
show yet (G05/O12). The start year is 1990 or 1992. **Review** comes before **Start career**.
Browsing, review and starting write no save; the new career is saved only when you save it.
Arrows choose, Enter accepts and Esc goes back. [designed: owner, 2026-10-21; T88] On the
country list, **Space** (or **Players**) shows that country's twenty: role codes on the left,
squad then bench, and each player's complete card on the right. The card has the name with
initial, role code, age, caps, goals, height, foot, readiness, national and club position, cards,
performance (raw; its meaning is not decoded), the twelve skill bars with their values, the five
characteristics with bar, value and the original's word, and the tactics and mark line. Every
value equals what the original's own player screen prints [confirmed: F008, E007]. No attribute
total is shown. [designed: T89] The browse page shows
the selected country's card in the original's structure: manager; ranking now; formation with
the eleven's role codes; first fixture; the three team tactics and the five player defaults.
Status, skill, top ranking, strips, team skill and performance bars and the characteristics
aggregates read "not decoded yet (G05)" until archaeology decodes them. [designed: T101] The
window is one fixed page, scaled (below): at 900×640 it shows the same page smaller, and the long
country and player lists are windows of rows that follow the selection, as the original's are
([original start, load and save](original-game/startup-save-replay.md)).
`--resume <save>`, or `--country <n>` with `--template`, still opens management directly for
scripts. Check it with `python3 tools/desktop-ui/launch.py --template … --data …`, offscreen and
under `QT_QPA_PLATFORM=xcb xvfb-run -a -s "-screen 0 3200x2000x24"` with `QT_SCALE_FACTOR` 1 and 2.

```sh
python3 -m goal2.desktop --resume .cache/desktop.g2save --data .cache/GOAL.DAT
```

[designed: owner, 2026-10-22, #308, #321; T105] **The core route.** `--core` opens the same main window over the
original's own game, run as goal2's core (docs/core.md), instead of the Python route's game:

```sh
python3 -m goal2.desktop --core .cache/e006-r0001-main.sav --data .cache/GOAL.DAT --save .cache/desktop.g2core
python3 -m goal2.desktop --resume .cache/desktop.g2core --data .cache/GOAL.DAT
```

The window's model is a `CoreModel` (`goal2/desktop/core_model.py`; `window.window_for` picks the window by the
model). It keeps the original at its manager menu, moves it only by the original's own keys through the driver
(`goal2/core/driver.py`), and reads every value from the original's memory (`goal2/core/views.py`); it never
writes a byte into it, never reads the text page and shares nothing with the Python route's `DesktopModel`.
**Country** is the original's manager menu [confirmed: `docs/original-game/images/manager-menu.png`]: *Name /
rating*, *Team* with its world and continent rankings, *Next opponents* with theirs and the fixture's kind (as
`friendly home`), the *Managers* board 1–6, the menu's routes and the squad strip; **history** is its second view,
in the original's boxes (statistics, successes, results, top scorers, top caps, records). **Fixtures & match** has
the original's fixture list (sixteen rows at a time, Up/Down/PgUp/PgDn scroll, √ on the managed fixtures) and the
tournament (the managed country's group table and its fixtures; Up/Down change the group). These scrolls are
presentation only: no key reaches the original. [designed: T107, G12] **Team** is the original's SELECT YOUR TEAM
and team tactics [confirmed: `docs/original-game/images/m244-squad.png`, `m244-team-tactics.png`]: the roster strip
on the right (the eleven, a rule, the bench; Enter marks a player, Enter on another swaps them), the compact card of
the selected player with its bars (no number where a bar fits), the routes **Team tactics**, **Own tactics (T)**,
**Reposition (R)**, **Club position (C)** and **Rename (F2)**; the team tactics view's eight rows and the own tactics
view's four rows (and the marking row, which the original refuses outside a match) change by Enter. **Pool** is the
pool side of SELECT YOUR TEAM [confirmed: `m244-pool.png`]: the card on the left, a strip of the squad or of the pool's
eighty, 21 rows at a time, on the right (Left/Right switch them, Up/Down/PgUp/PgDn scroll); Enter marks, Enter on a
player of the other list exchanges them. Each edit is the driver's action (docs/core.md, "The Team and Pool route"),
run as a background job: the controls wait while the original presses its own keys, then the pages read the
original again. There is no draft, no Confirm and no captain: the original holds none outside a match. A refusal
shows the original's reason in the status line. [designed: owner, 2026-10-22, #331; T108, G14a] **Play next game**
plays the original's round (docs/core.md, "The round"), each step a background job: the round's other fixtures,
then their results as a goal2 page; the **captain** (the eleven in the roster strip: Enter kicks off with the selected
player as captain, the original moving its own highlight to him; C takes the original's own choice); the first half
as the original's quick result; at **half time** T102's bench, filled from the original (the eleven, the bench, the
original's substitutions-left counter, or its own "no more substitutes"; the half-time score): Enter on one and Enter
on one of the other group passes the pair to the original, which makes or refuses it with its message, and **Play
on** plays the second half; at a stoppage, the managed side's **substitution opportunity** (the bench, or let it pass
as with no key) and the same bench; then the result and summary, the table and each bulletin, one page at a time,
Next for the next, back to the Country page. An eleven the original refuses before the kick-off (EA09, "... has an
ineligible player in the first team") shows its message on the captain page, and **Players** opens SELECT YOUR TEAM
before the match, where Enter, Enter swaps two players by the original's keys. The pitch view over the core is G14b;
the round's page says so, and it never falls back to the Python route. **Save** (F7 in the original) writes the core save (`G2C1`,
docs/core.md "Saving"); `--resume` with a core save reopens it at the same manager menu (or at the round's stop it was
saved at), with the same views and the same memory. `--template` and every other route are unchanged.

[designed: owner, 2026-10-23; T109/T116] **Watch over the core.** On Play next game's captain page,
**Watch this match** is selected by default (owner demo feedback). Choose the captain and kick off;
turn Watch off explicitly for the quick result. The same pygame pitch window reads the original's
memory at its live polls, showing complete signed player/ball/official poses, role codes, score, minute and the
latest three commentary lines above the pitch. Space opens the full commentary; Esc closes it, or closes the pitch window when
commentary is hidden. Left/Right send the original's slower/faster keys, Up/Down change the marks. Each pose must be displayed and
acknowledged before the desktop advances the original. No unseen backlog plays on after the viewer closes:
**Resume watching** restarts the pitch at the core's current wait; Save can preserve that wait for `--resume`.
Enter in the pitch sends the original's Enter to open its pause menu and shows the bench in the desktop. At a
pause, Enter requests or cancels a substitution; the pair is chosen at the original's next substitution
opportunity. Half time offers the ordinary bench directly. The original makes or refuses every pair. The original's
summary-save question offers **Save summary…** (a readable UTF-8 text file) or **Continue without saving**.
[designed: owner choice, 2026-10-23] Both continue with N to the original's DOS writer; only the desktop exports
that summary. The Python route keeps its existing watched match controller and bench.

[designed: T116] Watched steps execute all original player polls but retain a snapshot only at a complete pose
or a manager decision. Live frames update the pitch instead of rebuilding the hidden desk, Team and Pool pages;
decisions refresh those pages. Kept snapshots are immutable, with read-only image readers sharing their bytes.
New watched matches use the original's fastest setting (delay 0), selected by queued Right keys before the first
complete pose; its bottom speed strip shows six chevrons at delay 0 down to one at delay 5. Save/resume keeps the saved speed.
The core pitch transports Enter/Left/Right in order with bounded, checked input history. The Python route keeps
its existing presentation-rate controls. No calibration, speed or substitution byte is patched directly.

[designed: owner, 2026-10-22; T106, #308's G10] **A new career on the core route.** `--core-boot` opens Launch
over the original's own new game, booted from the state at the program's DOS date call (`e039-r0005-date-call.sav`,
docs/core.md "Booting at the DOS date call"); GOAL.DAT is read at run time from `--data`:

```sh
python3 -m goal2.desktop --core-boot .cache/e039-r0005-date-call.sav --data .cache/GOAL.DAT --save .cache/desktop.g2core
```

**New career** offers the start year as the Python route does (1990 or 1992). The core answers the DOS date
`start − 1`/10/04, which the original turns into that start year [confirmed: NG-9], and presses N while the title's
tune plays (`Core.boot`'s `title_key`), then Enter on the player count (one manager). The country list is the
original's browser in its own order and the card is read from the core's memory (`views.country_select`,
`views.country_card`); the players page (Space) waits for the player card over the core (G12) and is hidden. The
review page takes the manager's name (14 characters at most, initial and surname, as the original's name entry
keeps it) and names the start year and stage the original set. **Start career** plays the original's keys to its
first manager menu (`Driver.new_game`); its bulletins are shown as goal2 pages, the original's three stories read
from its page buffer (`views.bulletin`), Enter for the next, and the last opens the main window above.

[designed: T115, #308's G13e; confirmed: F030 at archaeology 53d7ef5, 000E:6BD0] **Original round pause.**
A core reaching or saved at the original round's PAUSE opens its structured results and full message.
Continue/Enter sends the original key and keeps subsequent result pages before the captain or manager menu.
The current fixture is included, because the original has not incremented its index yet. Team edits stay locked
for the round, and controls/save wait during the background continuation. This adds pause recovery, with no new
live round-control UI.

[designed: T118, #308's G13f; confirmed: F015/F030 at archaeology 53d7ef5, E031 checkpoint3874]
**Shootout decisions.** Resuming the original announcement shows its message and match context.
Choose shootout order opens the XI beside the selected player's complete card. Select an available,
unchosen player with Enter; numbered names retain the order and Esc undoes the last pick. Every available
XI player is required. Saving a partial order and reopening retains the actual original decision.
Finishing the order opens the pitch for the original kicks, then its full-time summary-save question.
Team edits remain locked for the round, and decision controls wait during a background action.

[designed: T119, #308's G13g; confirmed: F015/F030, original callers9B42/9B70]
**Extra time.** The original start-of-extra-time and extra-time-half-time menus open the bench
with distinct phase labels. R/C, substitutions and Play go through the original menu, using its
remaining counter; this adds no new substitution allowance. Both intervals save/resume exactly,
keep round/busy guards, and continue through the original halves into the shootout decision when tied.

[designed: T110, #308's G13a] **Bulletins keep all three papers.** The new-career and round pages share the
three-column view: each paper has its masthead and all its story lines, as literal text, with no scrolling or
eighteen-line truncation. Next/Enter keeps the page sequence. The round's type fits alongside the sidebar; the
whole fixed page scales as usual.

[designed: T111, #308's G13b; confirmed: F023 and the original 9028/91CE/9509 routines] **Continental finals.**
The tournament page shows the two finals groups with their fixtures and top scorers, then the continental bracket
with its semi-finals, third-place fixture, final and places. The bracket's countries, scores and winner markers
come from the original's stored fixtures. Post-fixture bracket pages and the year's bulletins follow in the
round's normal Next sequence. The original advances the phase and ages the squad and pool; the desktop reads the
new state afterwards.

[designed: T113, #308's G13c; confirmed: F023 and original 9028/937C/9509] **World Cup finals.** The same pages
show all eight World groups and their fixtures, then the sixteen-slot knockout tree. Countries, scores, winners
and final places come from the original's stored fixtures. Top scorers switch to final places when the original
does. The queued round pages continue into the next continental campaign; save/resume keeps the core checkpoint.
Remaining match/decision prompts retain their following G13 scope (archaeology #390).

[designed: T114, #308's G13d; confirmed: F030/F031 and the original EA09/E44F routines] **Repair the eleven.**
When the original refuses an eleven with no goalkeeper or too many players in one position, its full message is
shown and the round remains open. On Players, **R - next position** and **C - club position** (also keyboard R/C)
let the original change the selected player before kick-off, at half time or a substitution stoppage. The selected
player stays selected through position changes. Repositioning spends no substitution; during position edits the last refusal remains labelled as historical, and Play asks the original
to validate again. At zero substitutions R/C shows the original's refusal. The controls wait while a job runs, and the pause's substitution request/cancel flow is unchanged.

[designed] Supply verified local game resources using the existing runtime-cache
instructions. No original resources or screenshots enter git. Without Qt the
entry prints the installation instruction and exits2; headless imports and quick
play remain Qt/Unicorn-independent. Linux Qt needs its platform libraries; X11
uses libxcb-cursor0 and libxkbcommon-x11-0 in addition to existing X/GL libraries.
Offscreen acceptance does not replace the actual X11 window check.

[designed: T74; renamed T90] Five destinations: **Country** (Ctrl+1, formerly Overview),
**Team** (Ctrl+2, formerly Squad & tactics), **Pool** (Ctrl+3), **Fixtures & match** (Ctrl+4)
and **Save** (Ctrl+5).

[designed: T90; accepted vision #266 screens 02/03/11/14] The window is the accepted original
style: black screens, DejaVu Sans Mono, cyan frames, a yellow country, gold labels, green values,
magenta hints and a yellow focus. A **top bar** shows GOAL2, the country, the career line
(manager / year / stage), the context and the next fixture; **[Top ^]** retracts it. A **side
bar** holds the five destinations; **[< Hide]** retracts it. [designed: T101] A small window
no longer retracts it (superseding T90's collapse below 1100 px): the page is scaled instead. A
retracted bar leaves its handle (**[v Top]**, **[Menu >]**) in one short row above the page.
**F11** hides both bars, or restores both when either is hidden. Retracting moves focus out of the
bar; restoring returns it. Page, view, drafts and selection are untouched. The browse-another-country selector is on the Country page. Role codes use the
original's line colours [confirmed: F008 `DS:699A`].

[designed: owner, 2026-10-22, #312; T101] **One fixed page, scaled.** Every screen of the
management window and of the launch window is composed once for a page of 1440×900 logical
pixels, as every original screen is one 80×25 text page [confirmed: `docs/original-game/images/*`].
The window scales the whole page uniformly to fit (scale = min(width/1440, height/900)), keeps its
aspect and fills the margin black; the page is never cut and never scrolled, and a small window
shows everything smaller, as the pitch window does (T94). The way is a scale applied to the whole
page (`goal2/desktop/fixed_page.py`): the page stays ordinary native Qt widgets, and every length
it is composed with is multiplied by the scale — the style sheet's pixel sizes (type, borders,
padding, minimum heights), the layouts' margins and spacings, the explicit widget sizes and table
rows — while the painted views (the strip, the player and country cards) draw in page pixels
through a scaled painter. It was chosen over a `QGraphicsView` holding the page, which scales
exactly but makes the view the window's focus widget, gives assistive technology the off-screen
proxy's geometry and turns drop-downs into scene items; with native widgets, keyboard, mouse,
focus, drop-downs (they open at the scaled place), dialogs and accessible names behave as at 1:1.
The menu bar and dialogs keep their 1:1 size. A part that does not fit the page becomes a **view**
of its page, reached by a route, never dropped: Country has the desk, **Country card >** and
**Other games >** (browse another country, start year, new campaign or friendly, return to the
active game); Team has the card and Team tactics; Pool has the browser and **Cards >**; Fixtures &
match has the preparation, the full-time result, **Half time >** (opened by itself when a pause
begins) and **Fixture list >** (next fixture, last result and resolution, goals and details, the
Play/Watch routes, standings snapshot, continental qualifying and **Competition table**). Esc
returns from a view to the page's first one. A drop-down is as wide as the page gives it; a long
entry is shown whole in its list. The shared check `fixed_page.problems(window)` (no scroll bar
visible, every visible widget inside the page and its parent, none squeezed below the size its
content needs) is what every screen task runs: `python3 -m unittest goal2.tests.test_fixed_page_t101 -v`
runs it on every page and view at 1440×900, 1050×780, 900×640 and 2560×1600, at Qt scale 1 and 2.

[designed: T91; accepted vision #266 screens 02/03/04] **Country** is the desk: *Your country*
(manager, world and continental rank), *Next opponent* (its ranks and the fixture), *Your
campaign* and *Last result*; the routes **Prepare match**, **Select squad**, **Pool**, **Fixture
list**, **Country card >** (the T89 card), **Manager name** and **Other games >**; the readiness line (`<n> ready / XI <k>`) and the captain; and
the twenty: `+` in the XI, `-` on the bench, the initial and name in the role's line colour, the
code and `C` for the captain. Enter on a player opens him on Team; the desk never changes the XI.
**Team** follows the original's squad screen [designed: T99; owner, 2026-10-21; confirmed:
`docs/original-game/images/m244-squad.png`]. The roster is a strip on the right of every Team view,
captioned with the country: the eleven in the draft's order, a rule, then the bench; each row is
the initial and name in the role's line colour with the role letter on the right, `C` for the
captain and `!` for an unavailable player. Up/Down select (across the rule), Space moves the
selected player between the XI and the bench under the existing rules (an unavailable player
cannot start; a preview or a running match cannot change). Left of the strip is the selected
player's complete card (T88), whose tactic words follow the draft; as in the original its twelve
skills are bars with no numbers and each characteristic is a bar with its word inside. Below the
card are **Pool / Compare >**, **Team tactics >** and **Rename (F2)**; the draft bar stays at the
foot of the page. There is no table view: the XI checks' table is a hidden model. [designed:
T101] **Pool** opens on the browser (outgoing player, filters, the eighty reserves, the selected
detail and the exchange); **Cards >** shows the complete cards of the outgoing (OUT) and incoming
(IN) player, one at a time, as the original's pool screen toggles between squad and pool
[confirmed: `docs/original-game/images/m244-pool.png`]; Esc returns. Ranks come from the
country records [confirmed: F007 via `goal2.game.country_card`].

[designed: T99; accepted vision #266 screen 16; owner playtest 2026-10-21, #304] **Team tactics**
holds, on the left, the team headed `<COUNTRY> / XI n / d-m-a` (the formation counted from the
drafted eleven's lines, never stored [derived: `goal2/game/country_card.py`]), the manager and the
captain (the strip lists the players); on the right, **TEAM DEFAULTS**, eight rows in the order
Defence system, Protection, Offside, Positioning, Possession, Passing, Tackling, Marking, each with
its current word. A row is element k's bit `1<<(k-1)`; its word is the first alternative when the
bit is clear and the second when it is set [confirmed: `docs/original-game/images/m244-team-tactics.png`; F010].
Space, Enter or a click switches the selected row; Up/Down move between rows. **Confirm plan** is
Confirm management; **Discard / Team** is Discard draft, then back to the roster. Team skills are
not shown: no aggregate is verified (G05). Escape returns to the card with the strip focused.

[designed: T92; owner, 2026-10-21; confirmed: E031 C15/C30] **Rename (F2)** on Team renames the
selected player (surname, at most 12 characters; the initial stays), and **Manager name** on the
Country desk sets the manager's name (at most 14). Both change the active game at once, like the
original's F2, keep any unconfirmed draft, and are refused in a preview or during a match. A name
is printable CP437, stripped of outer spaces; the original name removes a rename. Renames live in
the session save (version 4, written only when something is renamed) and never in `GOAL.DAT`;
every view reads names through the game. A new campaign keeps the manager's name.

[designed: owner, 2026-10-21; T93, #295] The national pool's 80 players carry common surnames of
the managed nation for the 32 best-ranked countries in GOAL.DAT and Greece
(`goal2/data/pool_names.json`, written for the rebuild, not real players). The original gives
every country the same mostly English pool names [confirmed: F002 R003, F007]; other countries
keep them. The names follow the managed country and are never saved; renames apply on top. The
pool search ignores accents ("kovacs" finds "Kovács").

[designed: T95; accepted vision #266 screen 05] **Fixtures & match** opens with the match:
the fixture's title, our eleven from the current draft and the opponent's stored eleven (the
computer may swap injured players at kickoff [confirmed: F024]), each with codes and formation.
The **Play** panel explains Quick (no pitch, the result at once) and Watch (the original on the
pitch, friendlies only) beside their buttons, and holds the watching speeds (the original
changes its speed with Left/Right over six steps [confirmed: E031 C39; 0791:9372]), which are
**Slowest** 10, **Slower** 15, **Slow** 30, **Normal** 60 (the default), **Fast** 120 or
**Fastest** 240 samples per second. It is chosen before kickoff, and **Left/Right** in the pitch
window step it during play, as in the original. It changes presentation only, never the result. The Country desk's first route,
**Prepare match**, leads here.

[designed: T94; accepted vision #266 screen 06] **Watching** opens the pitch window in the
original style: grouped side/score rows beside the fixture/minute and three-row commentary header, the pitch filling the
resizable window, each player shown by his one-letter role code (the managed side gold, the other
white), and the latest three commentary lines above the pitch. **Space** opens the full commentary, which also holds
the full-time board; wheel or arrows scroll it, End follows live, and Esc returns to play
[confirmed: goal2-archaeology E031 C08/C39c, E015 r0013, 53d7ef5; #306]. Esc on the pitch closes
the window. Sides
follow the original's positions [confirmed: F013]: a side attacking right has its right-side
players (B, M, W) below its left-side ones.

[confirmed: T96, static 0791:9372/05C6/0691/A3B6] In the pitch window **Up/Down** cycle the
original's five player marks: little men (☺, the player on the ball ☻), role codes (the
default, as in the original), arrows showing each side's direction, H/A, and shirt digits.
Keepers are always ☺. The referee and the two linesmen, who run the touchlines at the offside
line, are light-magenta ☺. Each mark fills one grid cell, so neighbours never overlap; on a shared
cell the last drawn in the original's order shows, and the ball hides under a player. With the
full commentary open, Up/Down scroll it.

[designed: T102, #305; confirmed: goal2-archaeology E031 C39–C41k, 53d7ef5; F027 E544] **The bench**
in a watched friendly. At half time, and at a stoppage the original offers (a substitution
opportunity), the pitch view freezes on the decision and shows the original's board (HALF TIME,
SUBSTITUTION OPPORTUNITY), and the goal2 window raises the bench in front: a view of **Fixtures &
match** that copies the original's in-match players screen. The eleven and the bench are in the
strip on the right (an injured player marked !), the selected player's card on the left, the
**substitutions left** counter from the original's decision (no more substitutes at 0), and the
prompt "take off this player" on a starter or "put on this player" on a bench player. Enter on a
player and Enter on one of the other group make a pair (v off, ^ on); **Play** (Tab, Enter) passes
the pairs to the original, and Esc drops the choice, or with nothing chosen plays on. At the
substitution opportunity that offers the pairs requested at a pause, Esc cannot cancel them: the
original's default answer there is what was asked for, so they are still made, the bench says so
("Esc: the requested substitutions are still made") and reports them as any answered swap
[confirmed: the vendored kit's `Match._on_notice`; #316]. The window
never decides whether a pair is legal: the original makes it or refuses it, and the bench then
shows the original's reason and its counter (a sixth substitution in a friendly: no more
substitutes). **Enter** on the pitch asks for the bench mid-play, as the original's Enter does
(the hint says `[Enter] Bench`; Space stays the commentary): the original pauses at its next key
poll, pairs chosen there are requests the original makes at the next stoppage, and the
substitution opportunity that follows offers them again. After the match the substitute stays in
the eleven, as the original's squad words keep it [confirmed: F029]; a substituted captain is
replaced by the incoming player [designed, as T47]. Closing the pitch view while the bench is open
cancels the match, as at any other moment. The text-only presentation (`frames=False`, kept for
compatibility checks) has no bench and plays on as before; the engine bridge refuses the bench
without the pitch samples, where the original takes the Enter [designed: #316]. An Enter the
original cannot take (after the final whistle, in the shoot-out) is dropped, and the next Enter
asks again [designed: #316].

[designed: T102] **Pacing.** The engine runs ahead of the pitch view, so it is paced: the worker
writes pitch sample k only after the view has acknowledged sample k − 64, and is never more than
64 samples ahead of what the player sees. 64 is the view's own bounded queue: the engine never
runs further ahead than the view can hold, and an Enter in play reaches the original within 64
samples of the frame on screen (about a second at Normal, 6.4 s at Slowest, a quarter of a second
at Fastest). Answers and acknowledgements reach the worker through a second private journal
written only by the parent, with the events journal's rules (`docs/watched-jobs.md`).

[designed: T97; accepted vision #266 screen 08] When a match ends, **Fixtures & match** opens its
result: FULL TIME and the score, the kind, half time and engine, each side's scorers, the
original's statistics (with regulation, extra time and penalties for a competitive match), the raw
possession/territory bars marked "meaning unverified", man of the match and the substitutions. A
quick result keeps only the score and goals; the rest reads "Not recorded". **Round results**
opens the table; **Continue** returns to the Country desk with **Prepare match** focused.

[designed: T78] Fixtures & results groups the next named fixture, last completed
score, engine provenance, goals and a read-only standings snapshot. Ordinary
goals retain source A/B order; competitive regulation, cumulative extra-time
score and penalty kicks appear separately. Qualification positions remain
provisional. A fresh country preview has its own empty result. Unavailable
Play/Watch routes show a reason and retain the existing callback refusals.
 Navigation moves
focus to the page heading and preserves unconfirmed drafts, the active game,
save files and running jobs. [designed: T77] National pool provides an outgoing
squad selector synchronized with the current squad row; it changes selection only.
Choose a visible reserve and read both full identities before exchanging.
Save/Resume and the editable save path live in Save / resume; Ctrl+S invokes the
same guarded Save. Status and Cancel match remain visible across destinations.
[designed: T101] Nothing scrolls: a part of a page that does not fit is a view reached by a
route (below); tables retain their native row/column navigation, and Tab moves to the next control.

[designed: owner, 2026-10-21; #283, #286] Squad and pool tables and details show each player's
role as the original's one-letter code (G S C b B D Ç m M F w W ¢ $; club role in details),
coloured by line, and the pool filter lists the codes with the original's position names. No
attribute total (the overall ability byte) is shown anywhere, including the browser UI.

[designed: T75; T90] The top bar shows the displayed country's full name (the T75 generic
shirt art is no longer drawn in it). Country shows that country's next fixture in
source A/B order and last result with its provenance, or an honest empty state.
**Return to active game** restores the active country and its unconfirmed draft;
New campaign and New standalone friendly remain explicit replacement actions.

[designed: #181] Selecting a country immediately shows a fresh campaign preview:
its name, twenty-player squad, captain, tactics, morale, next fixture and reserve
pool. Preview results belong to that fresh team; the active game's result is
shown again on return. **New campaign** or **New standalone friendly** explicitly
makes the selected country active; browsing never replaces the active game or
writes its save. Management, play, Save, exchanges and the competition table are
unavailable in a preview. [designed: #241; T101] The reserves table is a window of rows that
follows the keyboard and the wheel (no scroll bar); selecting a row shows its full-ID detail.
Preview XI checkboxes, captain and tactics remain read-only. Return to the active
country to recover its unconfirmed
XI/captain/tactics draft, or use Resume to load a saved game. Country selection
is unavailable during a match.

[designed: #181] A successful **New campaign**, **New standalone friendly**, or
**Resume** explicitly replaces the active game and discards any unconfirmed
management draft, after the question described below (T87). A Resume that fails validation leaves the active game and draft
unchanged.

[designed: T87; original save/quit: [start, load, save and quit](original-game/startup-save-replay.md)]
The **Game** menu holds **Save** (Ctrl+S), **Save as…** and **Quit** (Ctrl+Q); the Save page
has the same Save as. Before New campaign, New standalone friendly, Resume or Quit (menu,
Ctrl+Q or the window's close button), the window asks if anything would be lost. It names
**progress confirmed since the last save** (since the game was created, resumed or saved) and
an **unconfirmed squad, captain or tactics draft**. The engine's squad reorder after an
original match (#280) is not counted as a draft. It offers **Save and continue** (only when
there is progress to save), **Continue without saving** and **Cancel** (Esc). Save never confirms a
draft. A failed save shows its reason and nothing is replaced: the window stays open and the
previous save is untouched. Saving to a different existing file asks before overwriting. While a
match runs, saving is refused, and Quit warns that the match will be cancelled. Check it with
`python3 tools/desktop-ui/save-decisions.py --template … --data …`, offscreen and under
`xvfb-run` (xcb) at `QT_SCALE_FACTOR` 1 and 2.

[designed] **New campaign** starts a fresh campaign with initial seeds 4660/33590,
using the shared opening campaign generator. [designed: owner, 2026-10-20, T50] Its **Start year**
choice is 1990 (default; World Cup qualifying first) or 1992 (continental qualifying first,
[continental qualifying](continental-qualifying.md)); previews use the chosen year. A redraw or Resume does not regenerate
players; previews generate separate records. The displayed twenty records show
original names, position groups, ability, energy, confidence and eligibility;
team morale uses the confirmed eleven. Position groups use the runtime POS_LINE
mapping, not a new role table. The labels follow rebuild conventions, not an original Qt UI.

[designed; derived: T36/T44] Check exactly eleven available starters, choose one
as captain and toggle the eight tactics bits, then **Confirm management**. Until
confirmation, edits affect only widgets. **Discard draft** restores confirmed
choices. An unavailable selected starter can be removed; an unavailable reserve
cannot be added. Invalid drafts show a reason and preserve active state. IDs and
captain remain Python integers, including values above255. [confirmed: F010] Tactics
labels for elements1..4,6,7 follow F010; [designed] labels5 and8 retain the established rebuild choices.

[designed; derived: T33/T40] Save writes the confirmed state, never an unconfirmed
draft, through the existing atomic writer. Resume validates the save, embedded
template and rebuilt continuation before replacing active state. Invalid/missing
local files leave the current game and prior good save intact. DesktopModel calls
Python game/state/save interfaces directly and imports no web/Qt layer. Widget
updates stay on the Qt thread. Quick match execution uses the responsive T70 process flow below; pool
controls use the T71 flow below; original watched friendlies use the T66 flow below. No server/hosting
is involved in this management slice.

[derived: official Qt API documentation] The shell uses
[QApplication](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QApplication.html)
and real widget events driven by
[QTest](https://doc.qt.io/qtforpython-6/PySide6/QtTest/QTest.html).

```sh
python3 -m unittest goal2.tests.test_desktop_model goal2.tests.test_desktop_entry -v
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/acceptance.py --scenario management --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
xvfb-run -a env QT_QPA_PLATFORM=xcb python3 tools/desktop-ui/acceptance.py --scenario management --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
xvfb-run -a env QT_QPA_PLATFORM=xcb python3 tools/desktop-ui/acceptance.py --scenario launch --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
python3 tools/desktop-ui/prove-management.py
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/redesign.py --scenario overview --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --evidence-dir docs/evidence/T75/linux
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/country-selection.py --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
```

[designed: T70] Confirm management, then choose **Play quick friendly**. Simulation
runs in a local process; the window stays responsive. Controls that change the
game are disabled until completion. **Cancel match** or closing the window stops
and reaps the process; a failed/cancelled/stale result never changes the active
game. A completed result shows named teams, score and goal scorers. The setup is
the rebuild quick simulation, not original watched commentary or visualization.

[derived: T41–T46; designed: T70] Campaign play consumes only the next supported
friendly in source A/B order, retaining condition, eligibility, RNG and history.
Save and resume use the same complete continuation. Supported original competitive
fixtures use the separate Play action described below; Quick itself remains friendly-only. **New standalone friendly** explicitly
creates fresh selected-country records without a campaign ledger; confirm its
management before play. Repeat carries the prior result/player state forward.
Creating either new mode replaces the active unsaved game only on that explicit
action. Save writes confirmed state; unconfirmed management edits must be
confirmed or discarded before playing.

[designed: T70] The Qt-free worker exchanges explicit JSON session saves through
private temporary files, with one job in flight and UI-thread publication once.
A completion must match both the original state object and its complete encoded
state/template. Cancellation waits at most half a second for termination before
kill and a second bounded reap. Optional Qt remains outside headless imports.

```bash
python3 -m unittest goal2.tests.test_desktop_quick_jobs -v
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/acceptance.py --scenario campaign-friendlies --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/acceptance.py --scenario worker --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
python3 tools/desktop-ui/prove-friendlies.py
```

[derived: T45; designed: T71/T77] The National pool destination retains the twenty-player
squad membership. It shows eighty reserve identities with original names, source position
code/group, ability, energy, confidence and availability. Search names and filter
numeric position codes to find a reserve. These controls only filter the view.
Select an outgoing player and a reserve row, then **Exchange selected squad player and reserve**.
The raw reserve detail and exchange summary retain names and full integer IDs.
Filtering clears the incoming selection and shows an explicit empty detail; select
a visible row again before exchanging.
The exchange uses the confirmed team and discards unconfirmed widget edits.
T45 swaps full IDs, repairs a replaced starter/captain, and preserves player
records. Confirm management, save/resume or play with the exchanged team.

[assumed: T45 Q008/#254] The explanation beside the exchange action is authoritative:
exchanges require a pending supported managed friendly outside the provisional
tour boundary. This is the existing provisional rebuild policy, not established
original window fidelity. Invalid or unavailable incoming players are refused
without changing the game. Standalone mode has no national pool. [designed: T77] The adjacent reason also explains preview, standalone and busy
contexts. Pool controls are disabled while a match process is running. Redraw/filter/resume never
regenerate player identities; the existing ordered quick tail updates reserves
once per completed fixture.

```bash
python3 -m unittest goal2.tests.test_desktop_pool -v
QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/acceptance.py --scenario campaign-pool --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT
python3 tools/desktop-ui/prove-pool.py
```

[designed: T47] Campaign matches now pause for explicit
[halftime substitutions](campaign-halftime.md). Select an outgoing starter and
available bench player, use **Substitute**, then **Continue second half**.
No re-entry; friendly substitutions are unlimited. Saving is disabled while the
match is pending; cancel keeps the previous game/save. Standalone quick play
continues uninterrupted. Substituted XI/captain choices persist for later
fixtures and through full-time save/resume.


[designed: T66] To watch the next scheduled **friendly**, install the optional
presentation and original runtime dependencies in the same environment as Qt:

```sh
python3 -m pip install '.[desktop,watched,match-view]'
python3 -m goal2.desktop --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --save .cache/desktop.g2save
```

[designed] Confirm XI, captain and tactics, then choose **Watch original friendly**.
A separate Pygame window shows a numbered animated pitch, original ordered commentary, minute and score;
after the original post-match tail, scroll with the mouse wheel or arrow keys to
see the original full-time board, man of the match and **Raw rating**. Countries,
minute and score stay pinned above the scroll area. New commentary follows live
until wheel/arrow scrolling pauses it; End resumes following. Completion opens
at the original board, with raw ratings below. Escape or
the window close button closes it. Closing while the match is running cancels the
match and preserves the last committed state/save. Closing a completed viewer
keeps the published result. Save/Resume remain Qt actions; saving during a match
is unavailable. A second match requires an explicit new Play/Watch action.
Pending qualifiers, standalone watching, in-play tactics changes, mid-match saves and
competitive watching are unsupported; substitutions are made on the bench (above). Quick management/play remains available without
pygame-ce, Unicorn or watched resources; Watch reports the missing dependency.

[designed: T83] The field is a modern schematic. Team colors identify the fixture
countries; numbers 1–11 are current local pitch slots, not persistent shirt
numbers. The ball and players use discrete original completed-tick positions,
without interpolation or halftime rotation. Only the original exact hidden-position
sentinel suppresses a marker. The fixed default playback target is 60 samples per
second, independently of engine speed; slow display refresh can extend playback.
Score, minute and commentary follow the currently displayed sample's canonical
event watermark. The last tick stays on screen through full-time. Save and all
management mutations stay locked until every sample has been displayed and the
original result validated. Closing while playback is pending discards the pending
result even if the engine has finished. The bounded queue holds at most 64
unacknowledged samples; the worker's finite journal remains lossless within T82's
8192-frame/16MiB budget. `WatchedController.start(playback_rate=...)` accepts an
explicit 1–240 samples/s target; `frames=False` retains the text presentation for
compatibility checks. See [T83 evidence](evidence/T83/README.md).

[confirmed: F014/E012 §1 at424d5998076da1e4efc399c2715689ddb44d3e1a]
Raw ratings are the actual returned original player-record words at +0x12, not
confidence or a replay prediction. Blank is 0x7FFF; signed values above5000 have
the substitution encoding10000 removed. This view explicitly displays raw values,
not the original screen's 1..9 buckets. Commentary and names are decoded at runtime;
no original text resources or images are bundled here.

[designed] Tested optional dependencies are pygame-ce2.5.8 (SDL2.32.10),
Unicorn 2.1.4 and PySide6 6.12.0 on Linux/WSL. The viewer receives bounded private
JSON presentation records, never game state/Memory or engine input. Qt polls the
T65 worker and owns the single validated result publication. Viewer startup has
a10-second bound. Failed folder/stream allocation releases partial resources and
reports the original cause; the same controller can retry. Cancellation terminates
then kills/reaps only its owned engine
and viewer, each with half-second waits. Native Windows packaging is untested.

[designed: #236] The watched viewer retries Windows status replacement denial
(WinError5) for up to250ms. Qt defers status-read access denial to later polls,
without sleeping in the callback, for up to250ms of consecutive failures; a
successful read resets that budget. Native Windows reads may report errno13
without a winerror. Owned viewer-folder deletion retries WinError32 for up
to500ms after child reaping and stream closure. Permanent or unrelated errors
propagate. Failed teardown retains references for retry and keeps its pending
match lock; a completed old viewer never releases a newer job's lock.

See T66 evidence (`evidence/T66/README.md`, removed 2026-10-20; on branch `local`) for retained text-mode checks and
[T83 evidence](evidence/T83/README.md) for animated pitch display acceptance.

```sh
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy QT_QPA_PLATFORM=offscreen python3 -m unittest goal2.tests.test_pygame_pitch_view -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/animated-pitch.py
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy QT_QPA_PLATFORM=offscreen python3 -m unittest goal2.tests.test_pygame_match_view -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/watched.py
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy QT_QPA_PLATFORM=offscreen python3 -m unittest goal2.tests.test_watched_bench_t102 -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy QT_QPA_PLATFORM=offscreen python3 tools/desktop-ui/watched_bench.py
```

[designed] For validation, set TMPDIR to the checkout's physical `.cache/tmp` and
stage the verified fixtures described by the T66 evidence; these commands never fetch
or commits original assets. A normal desktop launch should use its native SDL/Qt
display drivers, not the headless variables above.


[designed: T80; derived: T51/E034 at424d599] For a supplied pending original
competitive fixture, the button reads **Play original competitive**. It runs the
original engine in a separate owned process with the fixture, current confirmed
XI/captain/tactics, engine year and both RNG seeds. Default decisions continue
play, with the existing five substitutions per side budget. The Qt window shows
live minute/score progress, then named regulation, extra-time, penalties and winner
labels where applicable. Only a validated full post-match continuation publishes;
Save/Resume retains its complete result, Memory and seeds. No competition draw or
new fixture progression is added. Unsupported kind4 still refuses Play.

[designed: T80] A loaded competitive automatic captain0 is displayed as the disabled
**Original captain selection** placeholder. Playing preserves that original input;
explicit **Confirm management** requires a named captain in the XI. Missing runtime
or local resources show install/resource guidance while management remains usable.
Competitive Play, friendly Quick and friendly Watch share one match lock. Save,
Resume and management edits wait until completion or cancellation. Cancel/close
reaps only the owned child and preserves the active state and previous save.
**Watch original friendly** continues to support scheduled friendlies only.

```bash
python3 -m unittest goal2.tests.test_desktop_competitive_jobs -v
python3 tools/desktop-ui/competitive_play.py
QT_QPA_PLATFORM=xcb xvfb-run -a python3 tools/desktop-ui/competitive_play.py
```

[designed: T76] **Team** (formerly Squad & tactics) retains the twenty-player source-order roster.
Select a player on the strip to read his card: role, positions, readiness and cards, energy and
morale (the confidence byte). The strip's grouped XI and bench reflect the private draft, with the
captain marked; grouping does not assign a formation. The fixed
Confirm management / Discard draft bar stays at the foot of the page in both Team views.
Space toggles the XI and the tactic rows; Enter switches a tactic row or activates a focused draft action.
Draft edits survive navigation and country preview/return; Save writes confirmed
state, and match play still requires confirmed management.

[designed: T76/#233; derived: native launcher diagnosis] Windows quick-worker
cleanup allows up to0.5seconds for a transient sharing violation while an owned
child finishes closing stderr. Other cleanup errors propagate. Cleanup failure
retains ownership so Cancel can retry; it does not publish a candidate or change
the confirmed save. Worker interpreter and dependency context remain unchanged.

[designed: T78] The fixtures/results acceptance scenario supports verified saved
inputs and separate native scale processes:

```sh
python3 tools/desktop-ui/redesign.py --scenario results --template .cache/e010-r0008-halftime.sav --data .cache/GOAL.DAT --evidence-dir docs/evidence/T78/linux
```

[derived: evidence/T78/README.md] The retained Windows proof runs this scenario
at measured 100%/200% with Qt 6.12.0 and the declared optional Unicorn 2.1.4 runtime
in a private validation directory. Host bootstrap and missing-runtime failures
are preserved alongside the final passing proof in T78 evidence (`evidence/T78/README.md`, removed 2026-10-20; on branch `local`).
Those setup corrections leave product code and the existing Windows environment
unchanged; dependency provenance is recorded without committing package bytes.

[designed: owner demo feedback, 2026-10-23; T117] The live pitch follows the original composition: three recent event lines above the field (oldest above newest), without history timestamps in that strip, and the » speed meter with the bottom control hints. Full commentary retains its timestamps and opens with Space. The header has the grouped side/score block plus the supplied fixture/minute; no named speed label remains above the pitch. E015-r0007 state 31 and the original 9372 speed loop establish the structure and six-step meter.

[designed: T120; confirmed: archaeology T88/T89] Core corner and goal-kick decisions show the original XI,
selected full player card and stored-pick marker. Up/Down, Enter, C, Esc and Space go through original keys.
Space opens the frozen pitch; Enter in that window or Return in management goes back to the same selector.
These decision waits save/resume exactly and keep the round's team-edit and worker locks. The original
remaining timer is preserved; the management screen holds the decision until the player answers.
Only the supplied role2/5 cases are covered; the remaining evidence limits stay on archaeology#400.

[designed: T121, owner .g2core decision] F7 opens the observed original save-name decision
on the Save page. Save/Cancel return through original Esc; Save writes the resulting playable
core atomically. A resumed terminal quit-save decision offers Save and close / Close without
saving, using the actual recorded pre-F10 origin rather than rewinding the quitting guest.
An imported terminal decision without that origin cannot be converted into a playable save.
Busy and round guards remain in force; ordinary host snapshots and old core saves remain supported.

[designed: owner#73, T122] New core careers declare Unlimited substitutions in friendlies
and five in competitive matches, shown before Start. The bench labels owner-policy friendlies
Unlimited; ordinary remaining counters stay exact. Legacy/imported saves keep their recorded
original policy, and loading never replenishes substitutions. The declaration survives regular,
partial-round and terminal save-and-close checkpoints.

[designed: #395; confirmed: source 44cea4de, 000E:0572/05F6 and the genuine G15-variant capture]
An original BEST PLACE YET achievement pauses the round with its caption and complete
three-column bulletin. Continue (Enter) supplies the one key the original consumes before
returning to management. The current achievement can be saved/resumed exactly; management
actions and save-name editing remain guarded during the round. Ordinary bulletins reserve
no achievement-caption space.

[designed: #409; confirmed: first T123 G15-variant campaign and source 44cea4de, 04F5/0572/05F6]
The original qualification congratulations also remains a guarded round page: its original
caption and all three bulletin columns are visible, and Continue supplies one original key.
An exact partial save resumes on that page. The original finite no-key animation and later
untimed wait remain available through the Core API; unsupported flags/callers stay explicit errors.

[designed: owner Windows playtest, #436; confirmed: F002/F008 player record +8/+9]
The Core Pool roster shows **CAPS** beside each name and its case-sensitive role letter.
This is the original unsigned international-appearance count, including zero. The column
follows the full player ID when paging or switching between the pool and squad; reading it
does not edit the player, run a match or change the save.

[designed: owner Windows playtest, #434/T134] **Compare >** on the Core Pool page shows the
selected pool player beside a team player. Choose the team player in **TEAM PLAYER**; both
names, roles, caps, skills and characteristics stay visible on the same scales. **< Pool**
or Esc returns to the list. Browsing a comparison changes no players. **Exchange these players**
is a separate confirmation, checked by the original game; a player who has left either list
cannot be exchanged again through a stale comparison.

[designed: owner Windows playtest, #435/T135; confirmed: original INSERT/F031 selection]
**Suggest** asks the original assistant to select a squad in an independent copy of the career.
It proposes recruitment changes and checks each next exchange with the original rules, leaving
the active career untouched. The comparison selector lists the proposals; its explanation names
the assistant's chosen position and the comparison pairing. No overall ability or new ranking
formula is shown. **Exchange these players** remains your explicit decision. After any career
change, ask again rather than applying an old proposal. **Cancel suggestion** discards a pending
query while its bounded copied step finishes; a query failure leaves the active game playable.

[designed: owner Windows playtest, #433/T136; scope corrected2026-10-26] Core pool identities
reuse the existing33 authored profiles: the canonical top32 countries plus Greece. Their80
surnames/initials remain unchanged. Names agree across pool, cards, team after recruitment,
comparisons, suggestions, scorers and commentary. Full player IDs and assigned country bind the
names. Unlisted countries, custom country-name mismatches and unavailable canonical data retain
the current original text. No extra-country list or fallback name generator is included
([policy and saves](pool-names.md)).

[designed: #433/T136] Original regeneration can pick a new initial and surname from the shared
bank. Covered full-ID/country slots retain their display aliases in this version, even when a
replacement's raw name, age and attributes change. This deliberate naming difference leaves
original regeneration untouched. Unlisted countries continue showing the current raw names.

Explicit original F2 renames take precedence, including original-bank names. Desktop saves
retain only optional rename-intent fingerprints, never generated aliases; guest memory/payload
and Core save version remain unchanged. Old saves receive the same covered-country policy
without migration. An old save without intent cannot distinguish a manually chosen bank name
from an automatically generated one; re-entering it through F2 records the explicit choice.

[designed: owner #430/T138] **SHOW MATCH (F8)** stays visible in the navigation sidebar,
including while browsing fixture lists, tournaments and round views. It brings the existing owned pitch
window forward; a minimized pitch is restored. This route remains available while the core is
busy. It sends no original key or new pose and preserves pending bench/taker decisions.

If a live viewer was closed, **RESUME MATCH WINDOW (F8)** reopens the current original pose
through the existing watching path. A stopped taker-pitch preview can likewise reopen without
dismissing its decision. With no available pitch/stop the action is disabled with an explanatory
tooltip. Desktop focus can be denied by a compositor; such a denial leaves the game/viewer alive.
Windows foreground permission is granted only to the owned child on this user-triggered action.

The separate pitch remains the current presentation mode. [Embedded pitch #446](https://github.com/diegoami/goal2/issues/446)
tracks integrating it into the main window; this navigation change does not implement embedding.
