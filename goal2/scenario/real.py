"""[designed: T86] Is the real backend configured? Report, never fetch.

The contract cases run against the real backend only when every item exists.
`reference_image()` downloads when its file is absent, so this module checks
paths itself and never calls it.
"""
import importlib.util
from pathlib import Path

from goal2.engine.original_match.assets import REFERENCE

ROOT = Path(__file__).resolve().parents[2]
NEEDS = {
    'quick': ('.cache/GOAL.DAT', '.cache/e010-r0008-halftime.sav'),
    'watched': (f".cache/{REFERENCE['asset']}",),
}


def missing(lane):
    """[designed: T86] Missing items for 'quick' or 'watched', in a stable order."""
    items = [path for path in NEEDS[lane] if not (ROOT / path).is_file()]
    if lane == 'watched' and importlib.util.find_spec('unicorn') is None:
        items.append("unicorn (python3 -m pip install '.[watched]')")
    return items


def not_configured(lane):
    """[designed: T86] The exact line printed for each unrun real case, or None."""
    items = missing(lane)
    return f"real backend: not configured ({', '.join(items)})" if items else None
