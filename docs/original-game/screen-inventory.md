# Classified screen inventory

The 29 rows below are the E015 classifier's current kinds. Each thumbnail opens a full 640×400 image. The image is embedded again beside its explanation in the relevant walkthrough or screen chapter as coverage expands. The table records one verified representative state per kind; materially different states and currently unclassified screens need their own images and descriptions. [confirmed: archaeology `static/screens/kinds.tsv`, `catalogue.tsv`, `tools/screens/render.py`]

| Kind | Original image | Source state | Current coverage |
| --- | --- | --- | --- |
| `dos-shell` | [Full screen](images/dos-shell.png) | E015-r0001 state 1 | Representative render; explanation pending |
| `title-load-prompt` | [Full screen](images/title-load-prompt.png) | E015-r0001 state 2 | Illustrated in [first session](first-session.md) |
| `title-player-count` | [Full screen](images/title-player-count.png) | E015-r0004 state 2 | Illustrated in [first session](first-session.md) |
| `country-select-name-entry` | [Full screen](images/country-select-name-entry.png) | E015-r0007 state 10 | Illustrated in [first session](first-session.md) |
| `country-select` | [Full screen](images/country-select.png) | E015-r0007 state 3 | Illustrated in [first session](first-session.md) |
| `bulletin` | [Full screen](images/bulletin.png) | E015-r0007 state 14 | Illustrated in [first session](first-session.md) |
| `manager-menu` | [Full screen](images/manager-menu.png) | E015-r0007 state 16 | Illustrated in [first session](first-session.md) |
| `fixtures-watch` | [Full screen](images/fixtures-watch.png) | E015-r0007 state 18 | Representative render; explanation pending |
| `fixtures-auto` | [Full screen](images/fixtures-auto.png) | E015-r0007 state 24 | Representative render; explanation pending |
| `round-playing` | [Full screen](images/round-playing.png) | E015-r0007 state 27 | Representative render; explanation pending |
| `round-results` | [Full screen](images/round-results.png) | E015-r0007 state 52 | Representative render; explanation pending |
| `match-watch-prompt` | [Full screen](images/match-watch-prompt.png) | E015-r0007 state 28 | Representative render; explanation pending |
| `match-menu-halftime` | [Full screen](images/match-menu-halftime.png) | E015-r0007 state 44 | Representative render; explanation pending |
| `match-menu-fulltime` | [Full screen](images/match-menu-fulltime.png) | E015-r0007 state 50 | Representative render; explanation pending |
| `match-menu` | [Full screen](images/match-menu.png) | E015-r0007 state 30 | Illustrated in [first session](first-session.md) |
| `match-live` | [Full screen](images/match-live.png) | E015-r0007 state 31 | Illustrated in [first session](first-session.md) |
| `match-commentary` | [Full screen](images/match-commentary.png) | E015-r0007 state 67 | Representative render; explanation pending |
| `match-summary-save-prompt` | [Full screen](images/match-summary-save-prompt.png) | E015-r0007 state 51 | Representative render; explanation pending |
| `match-summary` | [Full screen](images/match-summary.png) | E015-r0007 state 207 | Representative render; explanation pending |
| `squad-substitution-illegal` | [Full screen](images/squad-substitution-illegal.png) | E015-r0007 state 176 | Representative render; explanation pending |
| `squad-substitution-take-off` | [Full screen](images/squad-substitution-take-off.png) | E015-r0007 state 76 | Representative render; explanation pending |
| `squad-substitution-put-on` | [Full screen](images/squad-substitution-put-on.png) | E015-r0007 state 82 | Representative render; explanation pending |
| `squad-substitution-tactic` | [Full screen](images/squad-substitution-tactic.png) | E015-r0007 state 150 | Representative render; explanation pending |
| `team-tactics` | [Full screen](images/team-tactics.png) | E015-r0007 state 119 | Representative render; explanation pending |
| `captain-select` | [Full screen](images/captain-select.png) | E015-r0007 state 63 | Representative render; explanation pending |
| `save-game-name-entry` | [Full screen](images/save-game-name-entry.png) | E015-r0007 state 215 | Representative render; explanation pending |
| `quit-confirm` | [Full screen](images/quit-confirm.png) | E015-r0007 state 223 | Representative render; explanation pending |
| `save-game-prompt` | [Full screen](images/save-game-prompt.png) | E015-r0007 state 224 | Representative render; explanation pending |
| `file-not-found-prompt` | [Full screen](images/file-not-found-prompt.png) | E015-r0008 state 10 | Representative render; explanation pending |

The [provenance table](image-provenance.tsv) records both the full source savestate SHA-256 and the resulting PNG SHA-256. A savestate was matched to the source E015 manifest before rendering. The three earliest title/DOS states were fetched from the private E015 release; the others were found in retained local sittings. [confirmed: E015 manifests; renderer verification]

## Explicit capture gaps

- A pre-match 20-player squad and national-pool browse state with the full player card is needed beside the preparation step. The E031 guide gives actions, but its kept screenshot cache is absent in this checkout. [confirmed: E031 C27–C34; local cache inspection]
- Team and individual tactics, marking alternatives, injury/suspension cards, bench before/after a substitution, and condition changes need multiple states. The single classified images above cover only one state of each kind. [confirmed: E031 C31–C34, C41–C46; E015 screen catalogue]
- Tournament/history/standings, extra-time, shoot-out order and kicks, replay/highlights, save/load alternatives, campaign transition, and local multiplayer screens need targeted images; the E031 logged screens and released milestone saves are sources for those paths. [confirmed: E031 C16, C20, C23–C24, C47–C52; E031 README]
- `dos-shell` is the emulator's prompt before GOAL2, not a game navigation screen. `file-not-found-prompt` is a load error; it will appear in the save/load chapter. [confirmed: E015 state references in the table]
