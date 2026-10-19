# Corrected native status regression

[confirmed: report.json] The actual native controller read path and production writer pass three deliberately held-reader interleaves, validate the old packet/digest, retain pending state without publication, and publish a complete replacement. The same production functions also complete2000concurrent writes with normal actual-controller polls and no missing, sharing or packet errors. Owned read handles close and native writers are reaped. This is resource-free status-I/O proof, not match/UI acceptance.

[confirmed: host-receipt.json and collection.json] Tested source89c1f5df96ae1f6fbcc6cabe3c8c9cc95443ad35;179source and6protected launcher/save/original hashes remain unchanged. Collection preserves exact native UTF8/CRLF bytes in hashed envelopes alongside LF reading copies.

[confirmed: neighboring native-control-*-02 reports] Removing reader delete sharing, restoring the legacy writer, or bypassing the production read factory each triggers the intended rejection again. Linux ownership-controls-01 separately proves all three cleanup assertions fail when the respective close is removed, restoring all source bytes after each control. Native full match/scales require their separate acceptance evidence.
