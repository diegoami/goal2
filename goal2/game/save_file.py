"""[designed: T33, T170ay] Atomic replacement for encoded game saves."""

import os
import tempfile


def write_atomic(target, data):
    temporary = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent, prefix=f'.{target.name}.',
                                         suffix='.tmp', delete=False) as stream:
            temporary = stream.name
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        temporary = None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass
