# Ownership deletion controls

[confirmed: report.json] Removing each raw-handle, CRT descriptor or rename-handle close fails the intended cleanup assertions, with all product source bytes restored afterward. These are unit-mock controls, not native I/O acceptance.

[designed: evidence preservation] Unittest emits a trailing progress space before a failing assertion. Exact log bytes remain in UTF8/SHA256 envelopes. Reading copies strip trailing horizontal whitespace; report log hashes bind raw envelope text, not the normalized reading copies. normalization.json records both hashes. No assertion or outcome changes.
