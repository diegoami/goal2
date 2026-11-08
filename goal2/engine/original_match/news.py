"""T122e: immutable original news-page memory and pure cell decoding.

[confirmed: F039; raw000E:05F6 copies 0xFA0 bytes from [DS:A96E] to
[DS:A96A] before celebration. 214B:026D/02C8 use 160-byte rows of
character/attribute pairs; F001's text page is80columns by25rows.]
The standard IBM PC glyph mapping matches runtime/decoders/manager.py's
canonical decoder (exhaustive oracle test), but this vendorable package has no
external runtime dependency. Unicode names glyphs; original custom font
appearance is not reconstructed here.
"""
from dataclasses import dataclass,field

ROWS,COLUMNS,CELL_BYTES=25,80,2
PAGE_BYTES=ROWS*COLUMNS*CELL_BYTES
BACK_BUFFER_PTR=0xA96E
_LOW='☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼'


@dataclass(frozen=True)
class NewsPageMemory:
    """One actual completed back-buffer snapshot, with immutable optional provenance.

    cells is exactly4000 interleaved character/attribute bytes. It stays private
    original memory: public evidence uses hashes, never these raw bytes. Optional
    fields are observations at05F6entry, not references to mutable route state.
    """
    cells:bytes=field(repr=False)
    buffer_address:int|None=None
    data_segment:int|None=None
    return_address:str|None=None
    country:int|None=None
    side:int|None=None
    manager:int|None=None
    flags_words:tuple[int,int,int]=(0,0,0)
    waiting_key:int|None=None
    pushed_back:bool=False
    key_code:int=0
    seed_words:tuple[int,int]=(0,0)

    def __post_init__(self):
        object.__setattr__(self,'cells',bytes(self.cells))
        object.__setattr__(self,'flags_words',tuple(self.flags_words))
        object.__setattr__(self,'seed_words',tuple(self.seed_words))
        if len(self.cells)!=PAGE_BYTES:
            raise ValueError(f'a news page has {PAGE_BYTES} bytes, got {len(self.cells)}')
        if len(self.flags_words)!=3 or len(self.seed_words)!=2:
            raise ValueError('news provenance requires three flag words and two seed words')


def capture_news_page(memory,**metadata):
    """Purely snapshot [DS:A96E] from a memory view exposing DS and read(linear,n).

    Machine and the sealed/PlainMem port views satisfy this small read-only
    interface. No register, memory, key policy, pushed-back key or RNG is changed.
    The caller supplies optional scalar provenance; it is copied into a frozen
    NewsPageMemory. This captures one current page, not earlier overwritten pages.
    """
    ds=memory.DS
    ptr=memory.read(ds*16+BACK_BUFFER_PTR,4)
    if len(ptr)!=4:
        raise ValueError('incomplete news back-buffer pointer')
    address=int.from_bytes(ptr[2:4],'little')*16+int.from_bytes(ptr[:2],'little')
    return NewsPageMemory(cells=memory.read(address,PAGE_BYTES),buffer_address=address,data_segment=ds,**metadata)


def _screen_text(payload):
    return ''.join(' ' if b==0 else _LOW[b-1] if b<32 else '⌂' if b==127 else bytes([b]).decode('cp437') for b in payload)


def news_pages(memory):
    """Return a tuple containing one page, that page a tuple of25exact80-column lines.

    memory is either an immutable NewsPageMemory or a live DS/read memory view;
    the latter decodes the CURRENT completed back buffer only. The route's
    news_history snapshots retain earlier pages, and Route.news_pages aggregates
    those in actual wait order. No whitespace is stripped, no control character
    becomes a line break, and attributes remain available in snapshot.cells.
    """
    snapshot=memory if isinstance(memory,NewsPageMemory) else capture_news_page(memory)
    chars=snapshot.cells[0::2]
    return (tuple(_screen_text(chars[r*COLUMNS:(r+1)*COLUMNS]) for r in range(ROWS)),)
