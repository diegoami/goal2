"""[designed: owner, 2026-10-22, #308, #321; T105] The desktop's model over the core: Qt-free.

The core route opens the original's own game (goal2/core, docs/core.md) and keeps it at the manager menu. Every
value the pages show comes from the original's memory through goal2/core/views.py; every move between the
original's screens is the original's own keys, pressed by the driver (goal2/core/driver.py). The model never writes
a byte into the core's memory and never reads the text page. It shares nothing with the Python route's
`DesktopModel` and its GameState (decision 7, docs/redesign-253/vision-reconciliation.md).

[designed] Routes the core cannot serve yet are named with the G task that brings them (#308's order after this
one, G10): `DISABLED`.
"""
import os
from pathlib import Path

from goal2.core import views

# [designed: T105, #308] The routes of the manager menu and of goal2's pages the core cannot serve yet, and the G
# task that brings each (#308's scope, in its order: G11 squad, pool, select team, tactics; G13 the match flow).
DISABLED = {
    'team': 'G11',          # team info's edits, select squad, tactics: the Team page
    'pool': 'G11',          # the national pool: the Pool page
    'play': 'G13',          # play next game: the match flow under the core
}
DISABLED_TEXT = {
    'team': 'Team edits arrive with G11 (squad, select team and tactics under the core)',
    'pool': 'The pool arrives with G11 (squad, pool, select team and tactics under the core)',
    'play': 'Play next game arrives with G13 (the match flow under the core)',
}


class CoreModel:
    """The original's game at its manager menu. `open(savestate)` starts a core from a savestate (a new game's
    first screen is the team-info browser; Esc leaves it for the menu); `from_save(path)` resumes a core save."""
    core_route = True

    def __init__(self, core, data_path, save_path):
        from goal2.core.driver import Driver
        self.core = core
        self.driver = Driver(core)
        self.data_path = None if data_path is None else Path(data_path)
        self.save_path = Path(save_path)
        self.driver.to_menu()

    @classmethod
    def open(cls, savestate_path, data_path, save_path):
        from goal2.core import Core, CoreError
        try:
            raw = Path(savestate_path).read_bytes()
            return cls(Core.start(raw).core, data_path, save_path)
        except (OSError, ValueError, CoreError) as exc:
            raise ValueError(f'Cannot open the core: {exc}') from exc

    @classmethod
    def from_save(cls, path, data_path):
        from goal2.core import Core, CoreError
        try:
            return cls(Core.load(Path(path).read_bytes()), data_path, path)
        except (OSError, ValueError, KeyError, CoreError) as exc:
            raise ValueError(f'Cannot resume the core: {exc}') from exc

    # -- the views, read from memory at the manager menu -------------------------------------------------
    @property
    def state(self):
        return self.core.wait.state

    def desk(self):
        return views.desk(self.state)

    def fixture_list(self):
        return views.fixture_list(self.state)

    def tournament(self):
        return views.tournament(self.state)

    def history(self):
        return views.history(self.state)

    def memory_sha256(self):
        return self.core.memory_sha256()

    # -- saving ----------------------------------------------------------------------------------------------
    def save(self, path=None):
        """[designed] The Save page (F7 in the original): the core save (docs/core.md, "Saving"), written whole to a
        temporary file and then moved over `path`."""
        target = Path(self.save_path if path is None else path)
        try:
            data = self.core.save()
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + '.tmp')
            temporary.write_bytes(data)
            os.replace(temporary, target)
        except OSError as exc:
            raise ValueError(f'Cannot save the core: {exc}') from exc
        self.save_path = target
        return target
