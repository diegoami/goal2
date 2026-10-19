# Remaining native completion stall

[confirmed: exact receipt, timing and all-thread stack samples] Frozen source16c169db63416578738752940634bd02d395b808. Actual Qt1x diagnostic completes both original matches with4439/4830frames, exact ACKs, parity/save/resume and cleanup, but first heartbeat1.1859221seconds FAILS the strict limit. Receipt INCOMPLETE, not acceptance. Exact original receipt SHA2568ff88d4faf8934b727a809db38abad50baef7a749d746f193ec39bf9be855936.

[confirmed: ui-thread-timing.json] Actual controller starts0.3745715/0.2569633seconds; encoding runs on the owned thread. The long controller poll takes1.1858003seconds after frameACK4438. A sample at2908.6040047 shows the owner thread in completed_candidate → campaign_rounds.silent_until_managed → silent_results → vendored quick_engine/savestate functions. The longest second completion poll0.8385819seconds is below the limit. This identifies this run's completion stall; it does not attribute every historic heartbeat gap.

[confirmed: completion-source-comparison.json] Publication, rounds, silent-results and sampled vendored engine files are byte-identical to accepted84af745c before completion rework. Main independently rehashes180sources,566runtime files,3resources and6protected files; protected before/after agree. Lossless raw envelopes retain exact native output; sampler closes.

[designed: owner, 2026-10-19] The owner explicitly extended existing #254 to completion preparation. Prepare the private candidate off the UI thread while preserving exact results, owner-thread stale checks/view/state swap, final-frame/complete ACKs, bounded cancellation/cleanup and once-only publication. Vendored engine code remains untouched. The original strict acceptance remains required.
