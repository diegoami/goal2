# Final source/evidence carry

[confirmed: native-proof-final.log] The independent-anchor native audit passes
for main's Qt1/2 fixed-source Windows run. Original native logs/captures/receipt/
runner are retained under ../windows/native-01; this audit reads retained proof
and does not execute Windows. Main holds the authoritative external receipt.

[confirmed: proof-controls.json and complete proof-negative-*.log] Scratch-copy
controls reject a wrong external hash, a rewritten tracked/original receipt pair,
and a tampered capture. Real originals and frozen product bytes stay unchanged.

[confirmed: complete-source-carry.json] All6307 frozen tracked paths outside this
task's evidence were compared byte-for-byte with dfed1519. Only evidence additions
follow native execution. The compact record binds the complete machine manifest,
retained privately; the git source carry and native176-source audit are independently
reproducible without reading a huge manifest. No product/helper/test changes occur.

[confirmed: premerge-source-freeze.log, provenance.log] The native source freeze
passed exact-head premerge75hashes/original exclusion and provenance16files. A new
clean exact-head premerge follows this evidence-only commit before PR readiness.
Raw evidence output whitespace remains immutable; source whitespace checks have
no exemption and pass independently of raw log formatting.
