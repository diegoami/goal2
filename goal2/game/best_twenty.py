"""[designed: T183a/#594] Copied native assistant operation, before worker/UI wiring.

[confirmed: F031; T125 0f9f87f4, selection 7fbfd2e9] E44F prepares SELECT
TEAM (E479/E484/52CC), then Ins invokes DC7E. This operation accepts an
original_match.state/2 at an outside-match manager context. It does not adapt
DesktopModel's separate calendar or make its inherited template authoritative.
"""
from goal2.engine.original_match import Image, port
from goal2.engine.original_match.machine import MEM_SIZE
from goal2.game import engine_tables


def _words(image, address, count):
    return [int.from_bytes(image.memory[address + 2*i:address + 2*i + 2], 'little') for i in range(count)]


def recommend(state, *, check_cancel=None, extra_places=0):
    """Return a completed private candidate; caller owns publication/refusal policy.

    No live input is mutated. The state includes original-owned refusal effects;
    callers must not publish it on refusal. All registered calls are real ports,
    never draw stubs or a Unicorn fallback.
    """
    if type(extra_places) is not int or extra_places not in (0,2,4):
        raise ValueError('additional assistant places must be0,2or4')
    if check_cancel is not None:
        check_cancel()
    tables = engine_tables.load()
    image = Image.from_state(state, tables)
    ds = image.DS * 16
    if image.memory[ds + 0xC1E] or image.memory[ds + 0xC1F]:
        raise ValueError('the assistant needs a manager context outside a match')
    game = image.far(0xA923)
    manager = image.memory[game + 1]
    if not 1 <= manager <= 6:
        raise ValueError('the assistant needs a current human manager')
    country = image.memory[image.far(0xA91F) + 3 * (manager + 128)]
    if not 1 <= country <= 128:
        raise ValueError('the current manager has no country')
    squad_at = image.far(0xA917) + country * 191
    if image.memory[squad_at + 0x2E] != manager + 128 or image.memory[game + 0x47 + manager]:
        raise ValueError('the assistant needs an active country manager')
    base = image.rd(0x6D18 + 2 * manager)
    pool_at = image.far(0xA927) + 2 * base
    if image.rd(0xA927) + 2 * (base + 80) > 65536:
        raise ValueError('wrapped pool storage is not a supported career')
    initial_squad, initial_pool = _words(image, squad_at, 20), _words(image, pool_at, 80)
    initial = initial_squad + initial_pool
    if len(set(initial)) != 100 or any(not 1 <= w <= 3060 for w in initial):
        raise ValueError('the assistant needs twenty squad and eighty distinct pool players')

    from goal2.engine.original_match.port.engine import PortMachine
    m = PortMachine(image.memory, image.load)

    class Keys:
        def key(self, site):
            m.wr(0xA976, 0x0D0D)
            return 13

        def keypressed(self, site):
            return True

    specs = []
    for registry, variant in port.load(['all']):
        real = port.Registry(registry.name, registry.doc)
        for entry in registry.entries.values():
            if entry.stub is None:
                real._add(entry)
        specs.append((real, variant))
    inst = port.install(m, specs, keys=Keys())
    # [designed: T183c] Cancellation observes the private operation only; it
    # never changes a guest answer, strength comparison or retained live game.
    if check_cancel is not None:
        m.at('1771:377E', lambda replay: check_cancel())
    result = dict(allowed=True, refusal=None, country=country, manager=manager)

    def message(replay):
        if m.stack_word(8) & 255:
            caller = m.where(m.stack_word(2), m.stack_word(0))
            result.update(allowed=False, refusal={'0791:DC3D': 'finals', '0791:DC68': 'tour'}[caller])

    m.at('214B:1765', message)
    # [confirmed: E44F E479/E484] The original manager and outside-match pane
    # preparation. The sort itself remains the original's registered routine.
    m.write(game + 1, bytes([image.memory[squad_at + 0x2E] - 128]))
    m.write(ds + 0xC20, b'\0')
    ss, sp = m.seg(0x3052), 0x3000
    m.far_call('1771:52CC', (country,), '0791:E491', ss, sp)
    m.set_reg('bp', 0x3456)
    m.run(m.lin('0791:E491'), fresh=True)
    if m.frames or m.reg('sp') != sp + 6:
        raise RuntimeError('SELECT TEAM preparation did not return with its original ABI')
    m.far_call('0791:DC7E', (), '0791:E788', ss, sp)
    m.write(ss*16 + sp, (0xE788).to_bytes(2, 'little'))
    m.set_reg('bp', 0x3456)
    m.run(m.lin('0791:E788'), fresh=True)
    if m.frames or m.reg('sp') != sp + 2:
        raise RuntimeError('assistant did not return with its original near ABI')
    if check_cancel is not None:
        check_cancel()
    image.memory[:MEM_SIZE] = m.read(0, MEM_SIZE)
    squad, pool = _words(image, squad_at, 20), _words(image, pool_at, 80)
    if set(squad + pool) != set(initial) or len(set(squad + pool)) != 100:
        raise RuntimeError('assistant changed the squad/pool identity universe')
    result.update(state=image.state(tables), squad=squad, pool=pool,
                  changed=(squad != initial_squad or pool != initial_pool),
                  recruited=[w for w in squad if w not in initial_squad],
                  calls={k: v for k, v in inst.calls.items() if v})
    if extra_places:
        # [designed: owner#777/T232] Keep the original20candidate intact.
        # The original strength calls use only private scratch execution after
        # its state snapshot; never copy that scratch memory into the reply.
        from goal2.game.extended_squad import balanced_extras
        rows=[];players=image.far(0xA91B)
        if result['allowed']:
            for word in pool:
                if check_cancel is not None:check_cancel()
                record=image.memory[players+20*word:players+20*(word+1)]
                position=record[6]
                if not 0<=position<14:
                    raise ValueError('additional player has an unknown original position')
                line=image.memory[ds+0xD5C+position]
                available=0<record[0xE]<0x80 and not record[0x10]&0xA4
                strength=0
                if line and available:
                    m.far_call('1771:377E',(word,),'0791:E788',ss,sp)
                    m.set_reg('bp',0x3456)
                    m.run(m.lin('0791:E788'),fresh=True)
                    if m.frames or m.reg('sp')!=sp+6:
                        raise RuntimeError('additional strength call did not return with original ABI')
                    strength=m.reg('ax')
                rows.append(dict(id=word,line=line,strength=strength,available=bool(available)))
            result['extra_squad']=balanced_extras(rows,extra_places)
        else:
            result['extra_squad']=[None]*extra_places
        result['calls']={k:v for k,v in inst.calls.items() if v}
        if check_cancel is not None:check_cancel()
    return result
