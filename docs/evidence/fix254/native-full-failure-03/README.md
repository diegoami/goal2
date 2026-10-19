# Full native run with corrected status I/O

[confirmed: native-1.log and observations/scale-1/report.json] Actual Qt1x passes both real original matches, complete state/Memory/both RNG/history parity, save/resume/repeat,4439/4830rendered samples with exact final frame and complete-board ACKs, bounded cancellation/cleanup, callbacks[] and no controller error. Measured maximum heartbeat gaps are0.6562019/0.7262415seconds, below the unchanged1second limit.

[confirmed: native-2.log and observations/scale-2/report.json] Actual Qt2x passes the same original test and both frame/complete ACKs, save/resume, callbacks[] and cleanup, with no status-file/controller error. Its first heartbeat gap is3.3455651seconds; the second is0.6488269. The separate strict responsiveness check fails. The overall host receipt remains INCOMPLETE; this is not accepted two-scale native validation. The cause of that pause is not established and no heartbeat or timeout assertion has been changed.

[confirmed: collection.json and host-receipt.json] Main independently rehashed179source files,566runtime files,3resources and6protected launcher/save/original files unchanged. All original failures and raw native text are retained. Status-I/O regressions are separately demonstrated by native-after-03 and the current three native negative controls; that evidence does not waive full-match responsiveness.
