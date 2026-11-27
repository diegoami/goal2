"""[designed: T170ay] Versioned persistence for a committed native campaign."""

import base64
from dataclasses import asdict
import json
from pathlib import Path
import zlib

from goal2.engine.original_match.image import Image, MEM_BASE, STATE_SCHEMA
from goal2.engine.original_match.machine import MEM_SIZE
from goal2.engine.original_match.port.tables import MODULE_SIZE
from goal2.game import engine_tables
from goal2.game.save_file import write_atomic
from goal2.game.season import canonical_hash
from goal2.game.season_publication import PublishedCall, SeasonCampaign


FORMAT = 'goal2-native-season'
VERSION = 1
_STATE_FIELDS = {'schema', 'load', 'header', 'tables_sha256', 'initialised', 'code_data', 'memory'}
_DOCUMENT_FIELDS = {'format', 'version', 'state', 'published', 'sha256'}
# [designed: T170ay] Retain the T111 image tail (17,055,744 bytes with memory).
# The document limit allows base64 expansion of the bounded image and its ledger.
_MAX_MEMORY = 32 * 1024 * 1024
_MAX_DOCUMENT = 48 * 1024 * 1024


class NativeSeasonSaveError(ValueError):
    """The native campaign could not be read, validated or written."""


def _validate_state(state):
    if not isinstance(state, dict) or set(state) != _STATE_FIELDS or state['schema'] != STATE_SCHEMA:
        raise ValueError('expected native state/2 fields')
    load = state['load']
    if type(load) is not int or load < 0 or load * 16 + MODULE_SIZE > MEM_SIZE:
        raise ValueError('invalid native load segment')
    if len(bytes.fromhex(state['header'])) != MEM_BASE:
        raise ValueError('invalid memory header')
    compressed = base64.b64decode(state['memory'], validate=True)
    decoder = zlib.decompressobj()
    memory_size = len(decoder.decompress(compressed, _MAX_MEMORY + 1))
    if not MEM_SIZE <= memory_size <= _MAX_MEMORY:
        raise ValueError('invalid native memory size')
    if not decoder.eof or decoder.unused_data:
        raise ValueError('invalid compressed native memory')
    image = Image.from_state(state, engine_tables.load())
    if len(image.managed_countries()) != 1:
        raise ValueError('a native save needs one managed country')


def _unique_fields(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError('duplicated native save fields')
    return result


def decode(raw, *, view=None):
    """Read the committed campaign without opening a worker or invoking a view."""
    if len(raw) > _MAX_DOCUMENT:
        raise NativeSeasonSaveError('native save exceeds its size limit')
    try:
        document = json.loads(raw, object_pairs_hook=_unique_fields)
        if (not isinstance(document, dict) or document.get('format') != FORMAT
                or type(document.get('version')) is not int or document['version'] != VERSION):
            raise ValueError('unsupported native save format or version')
        if set(document) != _DOCUMENT_FIELDS:
            raise ValueError('invalid native save fields')
        digest = document.pop('sha256')
        if digest != canonical_hash(document):
            raise ValueError('native save checksum differs')
        try:
            state = document['state']
            _validate_state(state)
        except (ValueError, TypeError, IndexError, KeyError, zlib.error) as exc:
            raise ValueError(f'invalid native state: {exc}') from exc
        published = document['published']
        if not isinstance(published, list):
            raise ValueError('invalid native ledger')
        return SeasonCampaign.from_committed(state, (PublishedCall(**row) for row in published), view)
    except (ValueError, TypeError, RecursionError) as exc:
        raise NativeSeasonSaveError(f'cannot read native save: {exc}') from exc


def encode(campaign):
    """Encode and validate the campaign's one committed snapshot."""
    state, published = campaign.committed_snapshot()
    document = {'format': FORMAT, 'version': VERSION, 'state': state,
                'published': [asdict(row) for row in published]}
    try:
        document['sha256'] = canonical_hash(document)
        raw = json.dumps(document, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode('ascii')
    except (ValueError, TypeError, RecursionError) as exc:
        raise NativeSeasonSaveError(f'cannot serialize native save: {exc}') from exc
    decode(raw)
    return raw


def load(path, *, view=None):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(_MAX_DOCUMENT + 1)
    except OSError as exc:
        raise NativeSeasonSaveError(f'cannot read native save {path}: {exc}') from exc
    return decode(raw, view=view)


def save(path, campaign):
    raw = encode(campaign)
    try:
        write_atomic(Path(path), raw)
    except OSError as exc:
        raise NativeSeasonSaveError(f'cannot write native save {path}: {exc}') from exc
