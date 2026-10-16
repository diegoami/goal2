# Live browser management, friendlies and acceptance

[designed: T35–T38] `acceptance.mjs` drives a real Chromium browser against the
Python server. The `management` scenario checks a non-Denmark country,
lineup/captain/eight tactics confirmation, the confirmed preview, reload, draft
cancellation, rejected invalid states, keyboard focus and mobile layout. The
`countries` scenario checks country switching, Python-sourced roster fields,
matchup and layout. The `friendlies` scenario checks a non-Denmark country,
confirmed custom lineup and tactics, explicit Play, named results, reload without
an extra match, return to team management and a second friendly. All read local
fixture paths only; the repository must not contain original savestate or
GOAL.DAT bytes.

```sh
PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs \
  node tools/browser-ui/acceptance.mjs --scenario management
PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs \
  node tools/browser-ui/acceptance.mjs --scenario persistence
```

The default smoke uses `.cache/e010-r0001-halftime.sav` and `.cache/GOAL.DAT`.
Use `--savestate`, `--goaldat`, or `--url` to point at another local fixture or
already-running server. Set `SCREENSHOT_DIR` to an existing directory to save
390px and 1280px captures.

For the live flow, start `python3 -m goal2.web .cache/<savestate>.sav
.cache/GOAL.DAT` from the repository root and open the printed localhost URL.
Choose a country, edit the lineup, captain and tactics on Squad, then press
**Confirm team** to update the Python-owned in-memory session. On Overview,
**Play friendly** explicitly runs one complete assumed friendly with those
confirmed choices. The busy state blocks another click while it runs; the
server consumes a one-use action token so a repeated request cannot run it
again. A failed run reports an error and leaves the authoritative session
usable. Reload and navigation only read the retained state; neither simulates
a match. The result shows the ordered teams, managed side, half-time and
full-time score, named goal events, match count and both retained seeds. Use
**Another friendly · Manage team** to return to the same country's squad with
the updated player energy and confirmed choices, then play again.

**Save session** writes `.cache/session.g2save` (or the path given with
`--save`); **Load saved session** checks its full state and continuation before
changing the live session. A new game starts with the existing savestate and
GOAL.DAT command above. Resume with
`python3 -m goal2.web --resume .cache/session.g2save .cache/GOAL.DAT`; this
requires the save and GOAL.DAT, but no original savestate path. To transfer a
session, copy the `.g2save` file to the other computer and pass that path to
`--resume`; keep a local GOAL.DAT there too. `.g2save` is the rebuild's versioned
JSON session format and does not claim compatibility with original binary
`.sav` files.

[designed: T41] **New campaign** creates a fresh managed team from country, even
start year and two explicit seeds, replacing the current in-memory session.
Save first to keep the previous session. Manage and confirm your team, then use
**Play scheduled friendly**. The next-fixture panel shows source team A/B order,
kind and stage; retained results stay in the campaign history across save/load
and process resume. Unsupported qualifiers disable Play with an explanation.
Country switching is fixed within a campaign; start another campaign to change
manager. Ordinary friendly sessions retain their existing flow. Scores still use
the existing assumed friendly runner while the original engine kit is integrated
separately.

```sh
PLAYWRIGHT_MODULE=/path/to/playwright/index.mjs \
  node tools/browser-ui/acceptance.mjs --scenario campaign-friendlies
python3 -m unittest goal2.tests.test_campaign_friendlies -v
```

[designed: T41] The campaign browser acceptance pins country 4, start year 1990,
seeds 4660/33590: two friendlies with ordered pairs (4,1) then (9,4), followed
by an unsupported kind-5 qualifier. It checks creation, confirmed management,
duplicate rejection, history, reload, Save/Load, a fresh server resume and mobile
layout. `SCREENSHOT_DIR` also captures the campaign at desktop and mobile sizes.

[designed: T41] Run `python3 tools/browser-ui/prove-campaign.py` for five
negative mutation proofs. It saves each source file before changing one site,
runs the targeted test in a fresh Python process, requires an assertion failure,
and restores the saved bytes in `finally`. Run it sequentially with other checks
in a clean task checkout containing the ignored local inputs.

[designed: T42] The campaign scenario also checks published energy changes and
that squad energy/post-recovery RNG survive process resume. Run
`python3 tools/browser-ui/prove-campaign-energy.py` sequentially for eight
behavioral mutation proofs; each restores saved source bytes in finally and
leaves the vendored energy module unchanged.

[designed: T43] Campaign acceptance checks changed confidence, player confidence
rows, result/confirmed team morale and process-resume equality. Run
`python3 tools/browser-ui/prove-campaign-confidence.py` sequentially for eight
confidence mutations; each requires a targeted assertion failure and restores
saved source bytes in finally. Neither vendored model is mutated.
