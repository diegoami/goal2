# Visible native test window preparation

[designed: #254] Before each actual Watch start, restore only the owned Qt test window if minimized, raise/activate it, process pending events and assert it is visible and not minimized. The existing heartbeat measurement still includes the actual controller start. Record window-state changes and reject minimization while the controller is busy. Both actual scales and every existing assertion remain required. No product source, timing budget, user desktop setting or unrelated window changes.

[confirmed: Python compilation] Preparation only: both files compile. Native Qt execution has not occurred. Main is waiting for the owner to confirm desktop availability before the next physical run. Prior failures remain preserved.
