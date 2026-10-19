# First session: from launch to a match

The screens below show a **sample**, using different retained sittings where a single continuous screen series is unavailable. Follow the controls in the text; read each picture for the information the original presents. The original DOS layout is evidence for decisions and context, not a required remaster layout. [confirmed: E015-r0001, r0004, r0007; E031 C11–C15, C35–C40]

## Start and choose a country

![Original title asking whether to load a saved game](images/title-load-prompt.png)

*Original title, `E015-r0001 state 2`, savestate SHA-256 `55ea9e307aa5…` (full hash in [image provenance](image-provenance.tsv)). The bottom line asks whether to load; this is a question to answer, not a menu selection. [confirmed: E015-r0001 state 2; E031 C11–C12]*

For a new game, answer **N**. Answer **Y** to load a saved `.GL` game; with several saves, the original presents a list, and Esc reaches name entry. The screenshot shows the question before either choice. [confirmed: E031 C11, C11b, C12]

![Original number of players selector](images/title-player-count.png)

*Player-count selector, `E015-r0004 state 2`, savestate SHA-256 `f4ec5c7194ef…`. The highlighted digit is the current choice; the printed hint gives Left/Right and Enter. [confirmed: E015-r0004 state 2; E031 C12]*

Choose the number of local managers with **Left/Right**, then **Enter**. The one-manager walkthrough continues below. With two managers, country and name selection repeat for each; the main menu later offers **next player**. [confirmed: E031 C12, C16, C16b]

![Original country-selection card for Denmark](images/country-select.png)

*Country browser, `E015-r0007 state 3`, savestate SHA-256 recorded in [image provenance](image-provenance.tsv). The center card shows the selected country's manager, rankings, formation, tactics, skill bars and characteristics; the right list places the selection among countries. This is Denmark in this retained state, while the later manager screenshot belongs to Italy. [confirmed: E015-r0007 state 3; E031 C13–C14b]*

Use **Up/Down** to browse the visible countries and **Left/Right** for the next group of 16. The card helps weigh the country's world and European ranking, squad strengths, current formation and tactic tendencies before choosing. **Ins** shows world ranking and **Space** shows country players; **Enter** selects the country. The meaning of every bar and shorthand still needs an individual field-by-field audit; a magenta bar should not be treated as a numeric rating without that evidence. [confirmed: E015-r0007 state 3; E031 C13, C14, C14b, C15; evidence gap: bar scale]

![Original manager-name entry over the country browser](images/country-select-name-entry.png)

*Name entry, `E015-r0007 state 10`. The name-entry line overlays the country browser; the bottom hint says maximum 14 characters, Enter accepts and Esc aborts. [confirmed: E015-r0007 state 10; E031 C15]*

Type a manager name and press **Enter**. The first typed character replaces the initial “Player” name in the observed session. [confirmed: E031 C15, C15b]

## Read the news and management hub

![Original Soccer Bulletin on three newspaper panels](images/bulletin.png)

*Welcome bulletin, `E015-r0007 state 14`. Newspaper panels report the new manager; the lower strip prompts “hit any key.” A later bulletin can carry competition and squad news, so it is part of campaign context. [confirmed: E015-r0007 state 14; E031 C66, C66b, C56, C59]*

Advance the bulletin with a key. The subsequent management hub puts the next opponent and country rankings beside the menu, so a manager can decide whether to inspect the team, fixture, competition or squad before proceeding. [confirmed: E031 C66, C66b, C17–C21; E015-r0007 state 16]

![Original Italy manager menu with next opponent and squad strip](images/manager-menu.png)

*Manager hub, `E015-r0007 state 16`. The left column names Italy, its rankings and next opponent; the middle has six actions; the right repeats the squad strip, including position abbreviations. The bottom line advertises function keys. The formation and player condition are one more key away in **select squad**. [confirmed: E015-r0007 state 16; E031 C17–C21, C27]*

Use **Up/Down** to move the menu highlight and **Enter** to choose. **Team info** opens country cards; **fixture list** shows the round and can mark another match to watch; **tournament** shows groups/results; **history** shows past results and statistics; **select squad** is where players and tactics can be changed; **play next game** advances to the next fixture. **F7** saves and **F10** asks to quit. These were observed as separate E031 actions, not inferred from the E015 key-burst map. [confirmed: E031 C17–C21, C25–C26]

## Prepare and watch

Before playing, inspect **select squad**. The recorded guide demonstrates switching between the 20-player squad and the national pool with **Left/Right**, replacing a squad player with a pool player, changing positions with **R/C**, and opening individual tactics with **T**. The squad's player card contains identity, role, characteristic bars and readiness indicators. This initial sample still needs a retained, verified *pre-match* squad image; the in-match bench image below is related but has different substitution controls. [confirmed: E031 C27–C34; evidence gap: first-session pre-match squad image]

![Original Greece versus Hungary pre-match menu](images/match-menu.png)

*Match menu, `E015-r0007 state 30`, a Greece–Hungary match observed in another branch of the sitting. It shows each side's lineup and formation, access to team tactics and players, plus tournament, match stats and **play**. The bottom hint offers Ins to toggle automatic action replay. This is an authentic example of the screen kind, not Italy's next match. [confirmed: E015-r0007 state 30; E031 C37]*

When the game presents the watch question, **Y** enters the watched branch and **N** chooses the quick branch. In your match, the menu's **play** opens captain selection; **Up/Down** moves the captain highlight and **Enter** accepts. The observed F030 finding says the highlighted computer choice stands after the timed wait, but a fresh player should press Enter deliberately. [confirmed: E031 C35, C37, C38, C38b; reviewed F030]

![Original watched-match pitch and bottom control hints](images/match-live.png)

*Live pitch, `E015-r0007 state 31`, again Greece–Hungary. The header has score and match context, text commentary sits above the pitch, the pitch marks players/ball, and the bottom legend displays speed, result, commentary and bench controls. The exact meaning of every glyph and the F9 suffix is still open in this guide. [confirmed: E015-r0007 state 31; E031 C39–C39c; evidence gap: glyph legend]*

During a watched match, **Left** slowed the game by one speed marker in E031; **Space** opened the commentary view; **R** produced a quick result from a live match. At halftime, a board offers Enter to reach the bench/menu, where **players** allows substitutions before **play** begins the second half. The guide reports five substitutions in a friendly and two in competition matches based on its observed screens and original manual. [confirmed: E031 C39, C39c, C08, C40–C41c; original GOAL.HLP]

At full time, inspect **match stats** before returning to the manager menu. The statistics board includes a score, scorers, corners, penalties, shots, fouls, bookings, cards, possession and territory; a later chapter will identify each label and source state. The first illustrated chapter will continue through that board, campaign return, save and load once those specific screenshots are placed. [confirmed: E015-r0007 state 51; E031 C24b, C51; evidence gap: complete first-session image sequence]
