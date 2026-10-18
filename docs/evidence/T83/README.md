# Animated pitch runtime evidence

[designed: T83] Run `python3 tools/desktop-ui/animated-pitch.py` from the task
checkout with the desktop, watched and match-view optional dependencies and the
verified ignored original fixtures staged in that checkout's `.cache`.
Set `TMPDIR` to its physical `.cache/tmp` directory. This acceptance launches
real Qt management controls and a real SDL child; it executes original matches.

[designed: T83] The script creates a fresh UTC timestamp directory for each run.
`acceptance.json` records successful checks; `failure.json` retains the completed
observations if a check fails. Each child writes post-flip `metrics.json` and PNG
captures for its observed half selectors and full-time board. Captures contain
rebuild UI pixels only. Memory is compared in process and recorded only by hash;
original assets, executable bytes, savestates and raw pose journals are excluded.

[designed: T83] Each selector's first and 300th discrete sample are captured by
ordinal, without classifying an engine reset or selecting favourable spacing.
Metrics record visible/hidden player counts, unique projected position counts,
overlap multiplicities and ball visibility for those samples. Timing metrics
record actual post-flip intervals and mean/maximum observed cadence; the fixed
configured rate is a target, with host-dependent rendering and scheduling costs.

[designed: T83] The first friendly uses the production default target of 60 discrete
samples per second. The second uses the supported target of 240 to shorten the
repeat and Save/Resume check. Both compare complete canonical state (including
Memory and both RNG seeds), ordered events and result against an independent
original continuation without the frame channel. The child wrapper observes
production rendering and display flips, checks every sequence is shown once,
and records pixel changes and both half selectors. It does not replace the
renderer, pace frames, or modify the product acknowledgement protocol.

[designed: T83] Additional probes exercise a slow SDL child, genuine SDL QUIT
after engine completion while animation is pending, malformed/stale child
acknowledgements, unchanged prior save bytes, locked mutation controls and
teardown while another owned quick job holds the model lock. All child processes
belong to the acceptance invocation; no shared process is stopped.

[designed: T83] For headless Linux set `QT_QPA_PLATFORM=offscreen`,
`SDL_VIDEODRIVER=dummy`, and `SDL_AUDIODRIVER=dummy`. For a real Linux display use
its actual `DISPLAY`, `QT_QPA_PLATFORM=xcb` and `SDL_VIDEODRIVER=x11`; provide any
staged xcb libraries through `LD_LIBRARY_PATH` when needed. Environment mode names
are retained in each receipt. A headless pass does not establish native display
acceptance; neither Linux mode establishes Windows acceptance.

[confirmed: offscreen-20261018-run1.log and retained failure.json] The first retained
offscreen run completed both original friendly comparisons, Save/Resume and all
4,540 then 4,616 discrete frame flips. Its acceptance setup then attempted to
start a quick friendly after the second match, where the campaign correctly
offered a competitive fixture. That unsupported probe failed before the
cancellation probes. The script now visits owned-only quick teardown after the
first friendly and closes the second viewer directly. The failed run and its
captures remain as diagnostic evidence; it is not a complete acceptance pass.

[confirmed: linked T83 runtime receipts] Complete acceptance passed in
[offscreen/dummy](20261018T115046.684495Z-offscreen-dummy/acceptance.json) and
[native xcb/x11](20261018T115405.988758Z-xcb-x11/acceptance.json). The retained
[offscreen log](offscreen-20261018-run2.log) and
[native log](native-20261018-run1.log) end in PASS. Each mode showed every sample
of both original friendlies, both half selectors and full-time; compared the
complete result, canonical events, full Memory and both RNG seeds with the
independent baseline; completed Save/Resume; and passed the pending-lock,
slow-close, malformed/stale acknowledgement and owned teardown probes. Maximum
observed presentation backlog was 64 samples. The two original continuations
ended with seeds `[30711,52877]` and `[42620,53091]` identically in both modes.

[confirmed: the same T83 runtime receipts] Measured post-flip cadence:

| Mode | Configured target | Samples | Playback seconds | Mean samples/s | Maximum instantaneous samples/s |
| --- | ---: | ---: | ---: | ---: | ---: |
| offscreen/dummy default | 60 | 4540 | 75.853 | 59.839 | 167.297 |
| offscreen/dummy repeat | 240 | 4616 | 22.759 | 202.776 | 420.967 |
| xcb/x11 default | 60 | 4540 | 75.821 | 59.865 | 176.974 |
| xcb/x11 repeat | 240 | 4616 | 22.721 | 203.113 | 372.532 |

[derived: the same T83 runtime receipts] Instantaneous values are reciprocals
of the smallest measured inter-flip interval, including recovery from scheduling
lateness; every sample still advances on a distinct display flip. These timings
exclude engine startup and the independent baseline. No exact real-time rate is
claimed. The native receipt records actual Qt platform `xcb`; each native
child's first flip records actual SDL driver `x11`, pygame-ce 2.5.8 and SDL
2.32.10. The offscreen match receipt predates adding those getters to the
wrapper: its requested environment forced offscreen/dummy. A separate
[metadata-only probe](offscreen-20261018-driver-metadata.log) records actual
offscreen/dummy with the same library versions; it did not run an original match.

[derived: T83 runtime capture counts] In both modes, the first friendly's
deterministic 300th sample within selector 1 has all 22 players visible at 22
unique projected positions; selector 0 has all 22 visible at 21 unique positions
(one exact overlap). The repeat has 21 then 22 unique positions respectively.
All four samples have zero hidden players and a visible ball. The first sample
of each selector has 22 visible players but only two unique positions, with
overlap multiplicities recorded in metrics; the renderer preserves those
original positions. Representative native captures are
[first half](20261018T115405.988758Z-xcb-x11/round-1/sample-300-selector-1.png),
[second half](20261018T115405.988758Z-xcb-x11/round-1/sample-300-selector-0.png)
and [full-time](20261018T115405.988758Z-xcb-x11/round-1/full-time.png).

[confirmed: retained controls and focused-02.log] Early control attempts
`controls-1792323435847560500` (weak visibility oracle) and
`controls-1792323450306122111` (consumption-test handler error) were rejected as
proof. `controls-1792323460829517928` subsequently proved four intended
assertion failures. Final `controls-1792324192619165076` proved five intended
failures, including premature pre-flip consumption and missing acknowledgement;
[focused-02.log](focused-02.log) records all seven final tests passing. The
[accepted pre-T83 baseline](before-1792324216575042931/baseline.log) fails all six
new behaviour tests at intended assertions; source bytes were restored exactly.
[cadence-before-01.log](cadence-before-01.log) records the intended cadence-drift
failure before the pacing correction. These negative controls are expected
failures, distinct from the rejected proof attempts and complete runtime passes.

[designed: T83] The two completed runtime receipts retain the boundary label
`owned-only teardown round 2`; that second-round probe closes an ordinary
completed viewer. The first round explicitly starts a newer Quick job and proves
owned-only teardown. The script now labels the second round `completed-viewer
close round 2`; this diagnostic wording correction changes no exercised action.

[confirmed: regressions-tail-01.log] The retained combined 57-test run passes
T66 text/Qt presentation, all ten strict T64 publication seeds, shared watched
workers, Quick/management and T80 competitive lifecycle/outcome regressions.
The receipt preserves its captured terminal tail rather than claiming an entire
streamed log. [confirmed: t82-regressions-01.log] All 21 T82 observation/frame
transport/publication tests pass, including both original seeds, every-tick raw
identity/coordinate checks and exact baseline parity. [confirmed:
provenance-01.log, links-01.log] Provenance verifies 16 unchanged engine files;
links/JSON pass. Final exact-head validation is recorded separately.
