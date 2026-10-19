# Observational heartbeat stall diagnostic

[designed: #254] Qt2x only. Transparently time actual controller start/poll, native CreateProcess and status exists/open/read/close calls without replacing results or errors. A separate owned thread samples the current process stack after a heartbeat gap exceeds0.4 seconds, including controller startup; it observes and writes diagnostic artifacts only. The actual Qt original-match/save/resume/parity flow and every strict assertion remain intact. The sampler stops and joins before final report. Product source remains unchanged.

[confirmed: Python compilation] Preparation only; both generated Python files compile. No diagnostic execution or acceptance claim yet. The ordinary both-scale full07 failure remains preserved.
