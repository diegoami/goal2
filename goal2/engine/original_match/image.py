"""Images of the original's memory, in the forms goal2 already holds (no original bytes here).

An image is the guest memory of a DOSBox-X 2024.03.01 savestate of goal (version 2) taken outside a match (the
main screen of a new game, or any later menu screen): its `Memory` component, which is a 0x78-byte header and then
guest physical memory from address 0 (runtime/driver/savestate.py, F001). goal2's GameState.mem is that component;
a savestate zip holds it as the zlib stream `Memory`. The image holds GOAL.EXE's code and data as the game loaded
them, so it is the original's bytes: it is never committed, only fetched by hash (assets.py).

Record layouts, each from a finding: the player array, 3061 records of 0x14 bytes at the far pointer DS:A91B, and
the country array, 129 records of 0xBF bytes at DS:A917 (F007; runtime/driver/players.py); a country's first 20
words are its squad (slots 1..11 the eleven, F029), +0x2D its team tactics (bit e-1 = element e, 214B:0C57 and
0CF4; F010, F026) and +0x2E its manager byte (0x80 + the manager when a human manages it, else its own number;
1771:0B77, 000E:01FA); the manager array at DS:A91F holds manager m's country at +3*(0x80+m) (F011); fixture n
(1-based) is the 8 bytes at [DS:A92B] + 8n - 8: +0 the watch mark (0xFE) or a score, +2 the kind (1 a friendly),
+4 and +6 the two countries (F023, F024, F030); the game record at DS:A923 holds the fixture index +0x26, the
fixture count +0x28 and the year word +0x38 (route_fixture 000E:6CA7; 0791:2648)."""
import hashlib
import io
import zipfile
import zlib

MEM_BASE = 0x78                 # the Memory component's header (F001, M:layout mem_header)
GOAL_DS_PARAGRAPH = 0x2581      # static/goal-exe/README.md
PLAYERS_PTR, PLAYER_SIZE, N_PLAYERS = 0xA91B, 0x14, 3061
COUNTRIES_PTR, COUNTRY_SIZE, N_COUNTRIES = 0xA917, 0xBF, 129
MANAGERS_PTR = 0xA91F
FIXTURES_PTR, FIXTURE_SIZE = 0xA92B, 8
GAME_PTR = 0xA923
TACTICS, MANAGER = 0x2D, 0x2E
NAMES_PTR, NAME_LEN = 0x9B6C, 11            # surnames, Pascal strings of up to 10 (commentary.py, 1771:2E93)
TEMPLATES, TEMPLATE_STRIDE, N_TEMPLATES = 0x00BE, 0x15, 67   # commentary templates (commentary.py)


def _relocations():
    from . import build
    out, a = [], 0
    for d in build.RELOCATION_DELTAS.split(","):
        a += int(d, 16)
        out.append(a)
    return out


def _where(offset):
    """An image offset of the code as the listing writes it: SSSS:OOOO."""
    from . import build
    seg = max(s for s in build.SEGMENTS if s * 16 <= offset)
    return f"{seg:04X}:{offset - seg * 16:04X}"


def build_problems(memory, load):
    """Where the image's code or the data the match reads differ from the registered GOAL.EXE (build.py, generated
    from it): [] when nothing does. Code: all of it (image 00000..2580F), relocated words with the load segment taken
    off. Data: the initialised data the measured matches read and never wrote (variables and goal2's state are
    not in it: the players, countries, seeds, clock and fixtures are elsewhere or written)."""
    from . import build
    base = load * 16
    code = bytearray(memory[base:base + build.CODE_SIZE])
    if len(code) < build.CODE_SIZE:
        return ["the image holds less memory than the program"]
    for r in _relocations():
        v = (code[r] | code[r + 1] << 8) - load & 0xFFFF
        code[r], code[r + 1] = v & 0xFF, v >> 8
    problems = []
    for i, want in enumerate(build.CODE_SHA256):
        a = i * build.CODE_BLOCK
        b = min(a + build.CODE_BLOCK, build.CODE_SIZE)
        if hashlib.sha256(code[a:b]).hexdigest() != want:
            problems.append(f"code {_where(a)}..{_where(b - 1)}")
    ds = (load + GOAL_DS_PARAGRAPH) * 16
    blocks = {}
    for start, n in build.DATA_RANGES:
        blocks.setdefault(start // build.DATA_BLOCK, bytearray()).extend(memory[ds + start:ds + start + n])
    for blk, want in build.DATA_SHA256.items():
        if hashlib.sha256(bytes(blocks.get(blk, b""))).hexdigest() != want:
            problems.append(f"data DS:{blk * build.DATA_BLOCK:04X}..{(blk + 1) * build.DATA_BLOCK - 1:04X}")
    return problems


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def find_load_segment(memory):
    """GOAL.EXE's load segment, from its DOS memory control block: an 'M'/'Z' MCB owned by the segment after
    it, named GOAL, followed by a PSP (CD 20); the load module starts 0x10 paragraphs after the PSP
    (runtime/driver/savestate.py find_program, T08)."""
    found = []
    for seg in range(0x50, 0xA000 - 1):
        a = seg * 16
        head = memory[a:a + 16]
        if head[0] not in (0x4D, 0x5A):
            continue
        owner = int.from_bytes(head[1:3], "little")
        if owner != seg + 1 or not bytes(head[8:16]).startswith(b"GOAL"):
            continue
        if bytes(memory[owner * 16:owner * 16 + 2]) != b"\xcd\x20":
            continue
        found.append(owner + 0x10)
    if len(found) != 1:
        raise ValueError(f"{len(found)} GOAL programs in the image's conventional memory (one is needed)")
    return found[0]


class Image:
    """The original's memory outside a match. `Image.from_savestate(zip bytes)` or
    `Image.from_memory_component(GameState.mem)`; `memory_component()` gives the same form back."""

    def __init__(self, memory_component):
        if len(memory_component) < MEM_BASE + 0x110000:
            raise ValueError("not a Memory component of a DOSBox-X savestate: too short")
        self.header = bytes(memory_component[:MEM_BASE])
        self.memory = bytearray(memory_component[MEM_BASE:])
        self.load = find_load_segment(self.memory)
        self.DS = self.load + GOAL_DS_PARAGRAPH

    @classmethod
    def from_savestate(cls, data):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            return cls(zlib.decompressobj().decompress(z.read("Memory")))

    @classmethod
    def from_memory_component(cls, memory_component):
        return cls(memory_component)

    @classmethod
    def from_bytes(cls, data):
        """A savestate zip (it starts with PK) or a Memory component."""
        return cls.from_savestate(data) if bytes(data[:2]) == b"PK" else cls(data)

    def memory_component(self):
        return self.header + bytes(self.memory)

    # -- reading ---------------------------------------------------------------------------------------
    def rd(self, off, n=2):
        a = self.DS * 16 + off
        return int.from_bytes(self.memory[a:a + n], "little")

    def far(self, off):
        return self.rd(off + 2) * 16 + self.rd(off)

    def players(self):
        base = self.far(PLAYERS_PTR)
        return [bytes(self.memory[base + PLAYER_SIZE * i:base + PLAYER_SIZE * (i + 1)]) for i in range(N_PLAYERS)]

    def countries(self):
        base = self.far(COUNTRIES_PTR)
        return [bytes(self.memory[base + COUNTRY_SIZE * i:base + COUNTRY_SIZE * (i + 1)]) for i in range(N_COUNTRIES)]

    def squad(self, country):
        rec = self.countries()[country]
        return [int.from_bytes(rec[2 * i:2 * i + 2], "little") for i in range(20)]

    def managed_countries(self):
        return [c for c, rec in enumerate(self.countries()) if c and rec[MANAGER] > 0x80]

    def fixture_index(self):
        return self.rd_far(GAME_PTR, 0x26)

    def year(self):
        return self.rd_far(GAME_PTR, 0x38)

    def rd_far(self, ptr, off, n=2):
        a = self.far(ptr) + off
        return int.from_bytes(self.memory[a:a + n], "little")

    def name(self, player):
        """The player's surname as the commentary prints it ([DS:9B6C] + 11 * player)."""
        if not player:
            return ""
        a = self.far(NAMES_PTR) + NAME_LEN * player
        raw = self.memory[a:a + NAME_LEN]
        return bytes(raw[1:1 + min(raw[0], NAME_LEN - 1)]).decode("cp437", errors="replace")

    def sha256(self):
        return sha256(self.memory_component())

    def build_problems(self):
        """Where this image differs from the GOAL.EXE the kit was made on ([] when it does not)."""
        return build_problems(self.memory, self.load)


def names_and_templates(read, ds, far):
    """Readers of the image's own text, at run time: `read(linear, n)`; returns (name(player), templates)."""
    templates = []
    for t in range(N_TEMPLATES):
        raw = read(ds * 16 + TEMPLATES + TEMPLATE_STRIDE * t, TEMPLATE_STRIDE)
        templates.append(bytes(raw[1:1 + min(raw[0], TEMPLATE_STRIDE - 1)]).decode("cp437", errors="replace"))

    def name(player):
        if not player:
            return ""
        raw = read(far(NAMES_PTR) + NAME_LEN * player, NAME_LEN)
        return bytes(raw[1:1 + min(raw[0], NAME_LEN - 1)]).decode("cp437", errors="replace")
    return name, templates
