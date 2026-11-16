"""[designed: T170t/#751] Season-only news framing; generic saves stay unchanged.

[confirmed: archaeology fb6d3093, F039/news.NewsPageMemory] Each snapshot
has 4000 raw character/attribute bytes and optional observed provenance.
"""
import base64
import binascii
from copy import deepcopy
from dataclasses import fields

from goal2.engine.original_match.news import NewsPageMemory, PAGE_BYTES

CELLS_SCHEMA = 'goal2/news-cells/1'
PAGE_FIELDS = frozenset(field.name for field in fields(NewsPageMemory))
OPTIONAL_INTS = ('buffer_address', 'data_segment', 'country', 'side', 'manager', 'waiting_key')


def _validate_page(page):
    if not isinstance(page, dict) or set(page) != PAGE_FIELDS:
        raise ValueError('invalid season news snapshot fields')
    if type(page['cells']) is not bytes or len(page['cells']) != PAGE_BYTES:
        raise ValueError('invalid season news cell bytes')
    for name in OPTIONAL_INTS:
        if page[name] is not None and type(page[name]) is not int:
            raise ValueError('invalid season news integer provenance')
    if page['return_address'] is not None and type(page['return_address']) is not str:
        raise ValueError('invalid season news return address')
    if type(page['pushed_back']) is not bool or type(page['key_code']) is not int or not 0 <= page['key_code'] <= 255:
        raise ValueError('invalid season news key provenance')
    for name, length in (('flags_words', 3), ('seed_words', 2)):
        words = page[name]
        if (type(words) is not tuple or len(words) != length
                or any(type(word) is not int or not 0 <= word <= 65535 for word in words)):
            raise ValueError('invalid season news word provenance')


def _observation(value, decoding):
    if not isinstance(value, dict) or type(value.get('news_pages')) is not tuple:
        raise ValueError('invalid season news sequence')
    value = deepcopy(value)
    pages = []
    for item in value['news_pages']:
        if not isinstance(item, dict) or set(item) != PAGE_FIELDS:
            raise ValueError('invalid season news snapshot fields')
        page = dict(item)
        if decoding:
            cells = page['cells']
            if (not isinstance(cells, dict) or set(cells) != {'schema', 'base64'}
                    or cells['schema'] != CELLS_SCHEMA or type(cells['base64']) is not str
                    or len(cells['base64']) != ((PAGE_BYTES+2)//3)*4):
                raise ValueError('invalid season news cell envelope')
            try:
                page['cells'] = base64.b64decode(cells['base64'], validate=True)
            except (binascii.Error, ValueError) as exc:
                raise ValueError('invalid season news cell encoding') from exc
        _validate_page(page)
        if not decoding:
            page['cells'] = {'schema': CELLS_SCHEMA, 'base64': base64.b64encode(page['cells']).decode('ascii')}
        pages.append(page)
    value['news_pages'] = tuple(pages)
    return value


def encode_observation(value):
    """Detached JSON-compatible news cells; tuple framing belongs to Server.send."""
    return _observation(value, False)


def decode_observation(value):
    """After generic tuple restoration, restore exactly the worker's raw data shape."""
    return _observation(value, True)
