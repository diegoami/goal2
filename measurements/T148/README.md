# T148 native scaling evidence

[designed: T148] The `native-scaling` jobs in `ci.yml` and `windows.yml` run
`measurements/T144/native_probe.py` through `run_native.py`, separately at Qt factors
1 and 2. Linux uses Xvfb, xfwm4, an isolated D-Bus session and XDG runtime; Windows
uses the hosted desktop. Both provide a 3840×2160 screen so factor 2 has room.

The existing probe checks native focus, visible widget/window bounds, actual bar
pixels and unchanged Core/fixture state. The wrapper verifies each measured device
pixel ratio, active focus, source/capture hashes and exact source commit. Only then
does `receipt.json` carry `native_ci_verified: true`.

Run on a prepared native desktop, with the original fixtures in `.cache/`:

```bash
QT_QPA_PLATFORM=xcb python measurements/T148/run_native.py --factor 1 --out /tmp/native-factor1
QT_QPA_PLATFORM=xcb python measurements/T148/run_native.py --factor 2 --out /tmp/native-factor2
```

On Windows use `QT_QPA_PLATFORM=windows`. Each output directory must be new. These
are native-window checks; they must not run after sourcing the offscreen cloud
environment. The CI jobs upload rebuilt-window PNGs, JSON receipts and logs through
an original-file refusal filter. Original files and private saves are never uploaded.

[designed: owner, T148] This is automation on virtual/hosted displays. It does not
replace the owner's physical-display playtest.
