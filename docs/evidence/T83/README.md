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

[designed: T83] The first friendly uses the production default rate of 60 discrete
samples per second. The second uses the supported rate of 240 to shorten the
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
