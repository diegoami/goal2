# Native timing attempt04

[confirmed: native-2.log and observations/scale-2/timing.json] The real controller acknowledges frame29, then later sees status absent and triggers its unchanged10second startup check. No complete match is claimed. Recorded successful calls have maximum status open0.1865284s, read0.0002844s, close0.0002191s and poll0.1972631s. The previous3.3456second gap is not reproduced by these timings; the missing-status cause is not established.

[confirmed: collection.json] Main independently rehashed179source files,566runtime files,3resources and6protected files unchanged. Callbacks remain empty and owned resources/widgets close. Forced child termination leaves no final viewer I/O timing snapshot; preparation05 adds periodic retained snapshots with a distinct prefix. The actual diagnostic launcher is native-timing-launcher.py. All strict assertions remain intact.
