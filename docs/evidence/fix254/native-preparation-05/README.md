# Existence timing preparation

[designed: #254] Preserve the real Path.exists result and record its elapsed time. After a false result, separately attempt a real shared native read and record whether the new packet is readable, then return the original existence result. Product decisions and strict checks remain unchanged. Viewer timing snapshots use a separate filename prefix and checkpoint periodically so forced cleanup retains measurements; they are excluded from the SDL metadata glob. This addresses a diagnostic artifact naming collision in preparation03, not a product behavior change.

[confirmed: syntax checks] Preparation only; no execution or acceptance claim at this checkpoint.
