"""[designed: owner #433/T136, continuing T93] Country-fitting presentation names only.

Authored T93 names are preserved. Other countries use the separately attributed CC0 profiles.
Myanmar uses complete personal names by the owner's choice. Original records remain untouched.
"""
from functools import lru_cache, wraps
import hashlib
import json
import unicodedata
from pathlib import Path
from goal2.game.pool_names import table, FIRST, COUNT


@lru_cache(maxsize=1)
def extended_profiles():
    """[designed: owner #433] Frozen country profiles, independent of guest player records."""
    path = Path(__file__).resolve().parents[1] / 'data' / 'pool_names_extended.json'
    return {int(number): entry for number, entry in
            json.loads(path.read_text(encoding='utf-8'))['countries'].items()}


def surname_key(family):
    """[designed: owner #433] Count spelling groups, not accents or article variants."""
    text = unicodedata.normalize('NFKD', family.casefold())
    text = ''.join(letter for letter in text if 'a' <= letter <= 'z')
    while len(text) > 4 and text.startswith(('al', 'el')):
        text = text[2:]
    return text


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
            profile = extended_profiles().get(country)
            if profile is None or profile['country'] != self.data.country_names[country]:
                raise ValueError('No matching country pool-name profile')
            if profile['kind'] == 'personal':
                # [designed: owner2026-10-26] Burmese personal names are complete units.
                names = tuple(profile['names'])
                if country != self.data.country_names.index('Myanmar'):
                    raise ValueError('Unexpected complete-personal-name profile')
                self._validate(names)
                self._names[country] = names
                return names
            families = profile['families']
            if len({surname_key(family) for family in families}) < 60:
                raise ValueError('A country pool needs at least sixty distinct surnames')
            # [confirmed: F002 R003/F007; ui/country_select.py] National players occupy
            # consecutive20-name blocks. GOAL.DAT's squad_20 contains POSITION codes, not IDs.
            first = 20 * (country - 1) + 1
            reserved = {self.original_name(word) for word in range(first, first + 20)}
            names = []
            # Use every family before repeating one. A reserved full name must not cause
            # a family to disappear from the eighty displayed identities.
            for index in range(COUNT):
                family = families[index % len(families)]
                for rotation in range(26):
                    initial = chr(65 + (index + rotation + country) % 26)
                    name = f'{initial} {family}'
                    if name not in reserved and name not in names:
                        names.append(name)
                        break
            names = tuple(names)
        self._validate(names)
        self._names[country] = names
        return names

    @staticmethod
    def _validate(names):
        if len(names) != COUNT or len(set(names)) != COUNT:
            raise ValueError('The country does not provide eighty distinct pool display names')
        if any(not name or any(ord(c) < 32 or ord(c) == 127 for c in name) for name in names):
            raise ValueError('Pool display names must contain printable text')

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
            # [designed: T136] The alias belongs to the full-ID/country slot. A replacement
            # keeps that display identity; original regeneration still changes its raw data.
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
