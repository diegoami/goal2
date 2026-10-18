# Visual and interaction specification

[designed: #182] All values below are proposal tokens, not original-game facts.
Use ordinary Qt widgets/layouts and a small shared style module. HTML is a design
study only. No web runtime, new font dependency or global application state owner.

| Token | Proposal | Use |
| --- | --- | --- |
| background / panel / raised | `#081c18` / `#102b25` / `#1a3b32` | Deep pitch-green shell; modest surface hierarchy |
| text / secondary | `#f5f2e8` / `#bbcfc5` | Primary reading and supporting labels |
| paper / ink | `#f3efe2` / `#17352c` | Roster/detail reading areas |
| accent / warning / error | `#c8f279` / `#ffd17a` / `#ffb4a9` | Primary action, draft/preview, error text |
| divider / focus | `#507365` / `#ffe799` | Borders; three-pixel keyboard focus ring with offset |
| nationality | separate three-color stripe + country name | Decorative identity; never the only selected-state cue |
| spacing | 4,8,12,16,24,32 logical pixels | Panel padding24; compact rows≥40; controls≥40 |
| corners / movement | 8px panels; 4px buttons; ≤120ms hover | Disable movement for reduced motion; no animated critical status |

[designed] Typography uses system sans (Qt platform default; prototype system-ui)
with a strong weight hierarchy:16px reading/body,14px compact data,12–14px
supporting labels (11px decorative uppercase metadata only),
24px section headings,40px country title,56px score at the large target. Scores
and numeric attributes use tabular figures. Original-style monospacing is limited
to tiny decorative wordmark and numeric board accents. No dependency on a copied
GOAL font. Accent orange/blue for sample countries is decorative and never reading
text on an untested background. Check WCAG contrast in the implementation:4.5:1
body and3:1 large text/focus/non-text boundaries; disabled text remains readable.

## Components and Qt composition

[designed] A `QMainWindow` retains ownership. Compose a persistent country header
and a five-destination navigation (`Overview`, `Squad & tactics`, `National pool`,
`Fixtures & results`, `Save / resume`) above a `QStackedWidget`. Native buttons,
comboboxes, checkboxes and accessible names remain; use logical layout constraints,
not a canvas of fixed widget coordinates. Keep existing automation object names
or supply adapters before changing them. Implementers choose module boundaries in
T74; later tasks change their page modules rather than all editing `window.py`.

- [designed] Country identity: name, original generic shirt symbol and simple
  national stripe; no federation badges or licensed kit. Unknown palette falls
  back to neutral with country name; identity must never depend on art coverage.
- [designed] Fixture card: named A/B sides in source order, fixture kind, prominent
  play action only when eligible, explanatory disabled reason beside it.
- [designed] Player row: XI checkbox, name/position, raw values, availability text.
  An adjacent detail card exposes the same fields with labeled bars only once
  their raw scale is specified. Captain uses both C and **Captain** text.
- [designed] Lineup board: group selected XI by existing position groups with
  counts; a pitch motif supplies football identity. Do not imply coordinates,
  formation, preferred positions or draggable player placement. Bench has nine
  records. The mockup deliberately uses grouped strips rather than false 4-3-3.
- [designed] Tactics: eight existing switches/masks in current display order, with accepted
  labels after #164;
  show both alternative strings and current checked state; no new presets or
  per-player overrides. Persistent **Draft** bar has Confirm and Discard.
- [designed] Result board: named sides, score, provenance, goals/empty-state;
  original boards/ratings only when supplied by validated original result data.
  Penalties are a separate stage line and never added to ordinary goals.
- [designed] Inline feedback: nonmodal status lives near actions, persists until
  the next relevant action, is announced through Qt accessibility; errors retain
  context. Save paths remain selectable/editable, with no invented autosave.

## Ownership and capability matrix

| Context | Display | Allowed action / guard |
| --- | --- | --- |
| [designed] Active game, clean | Country plus **Active game**; confirmed XI/result | Existing management, save, eligible play and exchange policy |
| [designed] Active game, draft | Same country plus **Unconfirmed draft** | Confirm/Discard; Save explicitly writes confirmed state; Play refuses draft |
| [designed] Other country preview | Prominent preview name/roster; **Preview · active game:…** | New campaign/friendly or Return; Resume; no save/play/confirm/exchange/standings |
| [designed] Worker busy / halftime | Active country, progress or private pending decision | Cancel always reachable; existing halftime controls only when applicable; no replacement/save/selection/exchange; publication remains once-only |
| [designed] Unsupported fixture / absent kit/viewer | Real fixture context and reason | No enabled speculative Watch/Play. Missing optional dependency is actionable; no silent alternate route |
| [designed] No result / standalone | Honest empty result / no campaign pool | No invented recent results, standings or reserves |

## Keyboard, layout and platform contract

[designed] Tab/Shift-Tab traverse country, navigation, current content then action
bar in reading order; arrow keys operate native selector/list; Space toggles XI
and tactics; Enter activates the focused button only. Ctrl+1…5 changes destination
without state mutation; Ctrl+S invokes guarded Save (never while busy/preview);
Esc closes a nonmodal detail or offers existing cancel behavior without silently
discarding state. Give every control an accessible name and all icon actions text.
Focus must move to the new page heading on navigation and return to the opening
control on detail close. Announce draft/preview/errors through accessible status;
Qt acceptance must test this rather than treating HTML behavior as proof.

[designed] Target1440×900 and1050×780 at100%; support900×700 by stacking secondary
panels and allowing a single content scroll region with actions reachable. At200%
scaling (or long names), reduce the heading/score sizes and stack fixture sides and
player detail; retain all values/actions via scrolling, not clipped widgets or
ellipsis-only names. No horizontal scrolling for the shell; a named roster may
have contained horizontal scrolling if necessary, with keyboard access to every
column. Windows native scaling/focus/font metrics require real screenshots and
QTest interaction evidence in each runtime task; Linux/browser screenshots alone
cannot satisfy this. Preserve launcher and saves on Windows.

[designed] Qt and Pygame share colors, typography intent, named A/B order, score
spacing and provenance label. T79 adapts T66's packet/render surface after it
merges; no fonts/assets/state copied from original game. Opening/closing the view
keeps Qt's job token and publication ownership. No transition starts a second
match. Stage1 is a commentary/result board, not a live pitch animation.
