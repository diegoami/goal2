# Live browser management, friendlies and acceptance

[designed: T35–T37] `acceptance.mjs` drives a real Chromium browser against the
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

The view is local and in-memory: closing the server discards browser-session
changes. The server continues to require an existing compatible friendly
savestate and GOAL.DAT; it does not construct a new game or recover unsupported
template states.
