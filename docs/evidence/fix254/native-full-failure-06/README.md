# Actual Windows full run 06 — failed

[confirmed: retained original receipt and reports] Frozen source022a75c38199f4b0e5b6be02c9ac4069f59bcad0. The original receipt is INCOMPLETE, not accepted native evidence. Qt1x completed both original matches, parity/save/resume, final frame and complete acknowledgments; maximum heartbeat gaps were0.840/0.720 seconds. Qt2x completed the first match and acknowledgments, but its8.829-second heartbeat gap failed the strict one-second limit and subsequent Save navigation failed.

[confirmed: scale-2/report.json] The Qt capture reports native bounds[-32000,-32000,-31840,-31972] and active:false, consistent with a minimized native window. This run cannot establish visible navigation or physical bounds acceptance. Controller errors and callbacks were empty; owned resources/widgets closed and import context restored. This observation does not explain the earlier timing/startup failures.

[confirmed: independent collection.json] Main rehashed179 archived source files,566 runtime dependency files,3 resources and all6 protected launcher/save files after the run; protected before/after hashes agree. Original receipt SHA256:1f204a8506dbf78bb2957f6aab6ab5476ca7c06377c78e1e3bd749f1116d44df. Raw envelopes preserve exact original bytes; reading copies normalize only recorded newlines. No originals or runtime binaries are included.
