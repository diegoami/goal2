# T223 The original's delay, at the time it asks for: measurements (Linux)

[derived: measured, the scripts and JSON here] One Linux host (the JSON names it: Python 3.13.18, x86-64),
T140's career (Italy, 2028, from the recorded date-call state; `goal2/tests/test_core_delay_t223.py`). *Before* is
the delay's loop executed under Unicorn with no wait (`Core.delays_served = False`, the core up to T222); *after* is
the delay served at its entry and the step waited by the model as the window does (`CoreModel.pacing`). Both reach
the same memory at the end of each stretch (`same_memory`). Nothing of the original is in these files.

## The same watched stretch at each speed: [linux.json](linux.json)

`measure.py`: the first 450 watched steps after the kick-off, the speed set by the original's Left/Right keys.

| speed | before (s) | after (s) | asked by the original (ms) | delays served | core per delay: mean / p99 / max (µs) |
| --- | --- | --- | --- | --- | --- |
| 0 | 4.000 | 3.990 | 112 | 68 | 85.6 / 178.7 / 178.7 |
| 1 | 28.036 | 20.754 | 20,318 | 20,214 | 88.2 / 181.8 / 7,228.6 |
| 2 | 35.967 | 30.753 | 30,276 | 20,214 | 89.2 / 177.9 / 1,384.1 |
| 3 | 46.616 | 40.750 | 40,234 | 20,214 | 91.9 / 183.5 / 2,303.0 |
| 4 | 56.880 | 50.699 | 50,197 | 20,215 | 90.1 / 195.8 / 2,272.7 |
| 5 | 67.423 | 60.653 | 60,155 | 20,215 | 88.0 / 183.7 / 2,465.3 |

After, the stretch lasts the milliseconds the original asked for plus about 0.5 s (the steps whose emulation is longer
than their delays: speed 0 has no match delay). Before, it lasted the emulator's time for the loops plus the
emulation: on this host the calibrated loop (4,279 passes a millisecond, calibrated at DOSBox-X's fixed 30,000
instructions a millisecond, T222) runs a little slower than real time, so each stretch took 6-7 s more than asked.
On a slower host it takes longer still (#455's native Windows run: 3.47 s for the wide shot's 1.75 s). The core's
own time per served delay (its hook `Core._on_delay`, timed with a wrapper that adds its own cost) is 85-92 µs on
average and under 0.2 ms at the 99th percentile; a few single calls of the 20,000 took 1.4-7.2 ms, the host's
scheduler or the collector interrupting them.

## #455's pause: the wide shot's step at speed 2: [linux-wide.json](linux-wide.json)

`measure_wide.py`: the one step of Signori's wide shot ("just wide of post", "GOAL KICK"), which asks 1,753 ms
(1,708 of them the whistle's notes), three runs each.

| run | wall time (s) |
| --- | --- |
| the loop executed (before) | 2.185, 2.084, 2.082 |
| served, no wait (a headless run) | 0.439, 0.384, 0.531 |
| served and waited (the window) | 1.755, 1.755, 1.755 |

Reproduce: `.cache/venv/bin/python measurements/T223/measure.py --output measurements/T223/linux.json` and
`.cache/venv/bin/python measurements/T223/measure_wide.py --output measurements/T223/linux-wide.json` (about 10 min
and 1 min; `.cache/` as in docs/artifacts.md). The Windows measurement is the owner's playtest (#705's gate).
