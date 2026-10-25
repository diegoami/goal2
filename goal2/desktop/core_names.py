"""[designed: owner #433/T136, continuing T93] Country-fitting presentation names only.

Authored T93 names are preferred. Other countries use families from their canonical squad,
not a claimed frequency ranking. Original records, explicit renames and saves remain untouched.
"""
from functools import lru_cache, wraps
import hashlib
import json
from pathlib import Path
from goal2.game.pool_names import table, FIRST, COUNT


class NamesPolicy:
    def __init__(self, data):
        self.data = data
        self._names = {}
        self._original_pool_families = frozenset(data.player_names[FIRST:])

    def names(self, country):
        if type(country) is not int or not 1 <= country < len(self.data.country_names):
            raise ValueError('A pool name needs a country1..128')
        if country in self._names:
            return self._names[country]
        entry = table().get(country)
        if entry is not None and entry[0] == self.data.country_names[country]:
            _, families, initials = entry
            names = tuple(f'{i} {f}' for i, f in zip(initials, families))
        else:
            families = []
            reserved = set()
            # [confirmed: F002 R003/F007; ui/country_select.py] National players occupy
            # consecutive20-name blocks. GOAL.DAT's squad_20 contains POSITION codes, not IDs.
            first = 20 * (country - 1) + 1
            for word in range(first, first + 20):
                family = self.data.player_names[word]
                reserved.add(self.original_name(word))
                if family and not any(ord(c) < 32 or ord(c) == 127 for c in family) and family not in families:
                    families.append(family)
            names = []
            for rotation in range(26):
                for index, family in enumerate(families):
                    initial = chr(65 + (index + rotation + country) % 26)
                    name = f'{initial} {family}'
                    if name not in reserved and name not in names:
                        names.append(name)
                    if len(names) == COUNT:
                        break
                if len(names) == COUNT:
                    break
            names = tuple(names)
        if len(names) != COUNT or len(set(names)) != COUNT:
            raise ValueError('The country does not provide eighty distinct pool display names')
        self._names[country] = names
        return names

    def original_name(self, word):
        return f'{self.data.player_initials[word]} {self.data.player_names[word]}'

    def resolver(self, state, explicit=None):
        from goal2.core import views
        mem = views.Memory(state)
        base = mem.far(views.PLAYERS)

        def name(word, original):
            if not FIRST <= word < len(self.data.player_names):
                return original
            # Original regeneration can pick another entry from the shared500-name bank.
            # A recorded F2 name wins even if the owner chose one of those same names.
            if explicit and explicit.get(word) == name_fingerprint(original):
                return original
            # Regeneration also chooses a fresh initial, independently of the surname bank.
            if original.partition(' ')[2] not in self._original_pool_families:
                return original
            country = mem.byte(base + views.PLAYER_SIZE * word)
            if not 1 <= country < len(self.data.country_names):
                return original
            if mem.country_name(country) != self.data.country_names[country]:
                return original
            return self.names(country)[(word - FIRST) % COUNT]
        return name


@lru_cache(maxsize=4)
def _policy(path, modified, size):
    from goal2.data import load
    return NamesPolicy(load(Path(path).read_bytes()))


def resolver_for(state, data_path, explicit=None):
    if data_path is None:
        return None
    path = Path(data_path).resolve()
    try:
        info = path.stat()
        policy = _policy(str(path), info.st_mtime_ns, info.st_size)
    except (OSError, ValueError):
        # Imported/custom snapshots keep their own names when canonical data cannot identify them.
        return None
    return policy.resolver(state, explicit)


def name_fingerprint(name):
    return hashlib.sha256(name.encode('utf-8')).hexdigest()


def explicit_from_save(data):
    """Optional desktop rename intent; no aliases or original-memory fields are stored here."""
    size = int.from_bytes(data[4:8], 'little')
    header = json.loads(data[8:8 + size])
    value = header.get('display_name_intent')
    if value is None:
        return {}
    if (not isinstance(value, dict) or set(value) != {'version', 'renames'}
            or type(value['version']) is not int or value['version'] != 1):
        raise ValueError('Unsupported saved display-name intent')
    renames = value['renames']
    if not isinstance(renames, dict) or len(renames) > 3060:
        raise ValueError('Invalid saved display-name intent')
    result = {}
    for word, fingerprint in renames.items():
        if (not isinstance(word, str) or not word.isascii() or not word.isdigit()
                or str(int(word)) != word or not 1 <= int(word) <= 3060
                or not isinstance(fingerprint, str) or len(fingerprint) != 64
                or any(c not in '0123456789abcdef' for c in fingerprint)):
            raise ValueError('Invalid saved player rename intent')
        result[int(word)] = fingerprint
    return result


def with_explicit_names(data, explicit):
    if not explicit:
        return data
    size = int.from_bytes(data[4:8], 'little')
    header = json.loads(data[8:8 + size])
    header['display_name_intent'] = dict(version=1, renames={str(w): f for w, f in sorted(explicit.items())})
    blob = json.dumps(header).encode('utf-8')
    result = data[:4] + len(blob).to_bytes(4, 'little') + blob + data[8 + size:]
    explicit_from_save(result)
    return result


def presented(method):
    """Scope a name resolver to one pure model-view call, restored even on an exception."""
    @wraps(method)
    def view(self, *args, **kwargs):
        from goal2.core import views
        resolver = resolver_for(self.state, self.data_path, getattr(self, '_explicit_player_names', None))
        if resolver is None:
            return method(self, *args, **kwargs)
        with views.display_player_names(resolver):
            return method(self, *args, **kwargs)
    return view
