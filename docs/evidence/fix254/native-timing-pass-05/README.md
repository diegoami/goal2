# Strict Qt2x timing diagnostic pass

[confirmed: host-receipt.json and observations/scale-2/report.json] Both actual original matches pass full state/Memory/RNG/history, save/resume/repeat, frame/complete ACKs, geometry, callbacks[] and owned cleanup. Heartbeat gaps0.8621624/0.8107313s remain below1s. This is Qt2x diagnostic execution, not complete ordinary two-scale acceptance.

[confirmed: observations/scale-2/timing.json] No false existence check was observed. Maximum exists/open/read/close durations:0.005710/0.194617/0.000416/0.000459s; maximum completed poll0.801229s. Earlier heartbeat and missing-status failures remain unexplained and retained. Product source and all assertions are unchanged.

[confirmed: collection.json] Independent post-run hashes verify179source files,566runtime files,3resources and6protected files unchanged. Raw native bytes remain in envelopes alongside explicitly normalized reading copies.
