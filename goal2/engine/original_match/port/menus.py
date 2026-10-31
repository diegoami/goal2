"""T74: the manager's menus, translated from their named view and instruction listings.

Keyboard entries keep the kit's existing semantic service boundary. MenuPlan supplies
compatibility keys; the Python bodies own the resulting state writes and retain the
original frames, cursor transitions and guest-call return sites. No menu code is
loaded or interpreted from the executable by this module.
"""
from . import Registry
from .contests import ss16, ss8
from .geometry import cbw, mul, imul
from .mem import PortError, s8, s16
from .restarts import _end
from .runtime import Regs
from .setup import guest, member, farg, rb, rw, w8, w16, player_of, squad_of

PORTS = Registry("menus", "the manager's decision menus and key services (T74)")
PORTS.variant('tactics-adjacent-bit', '1981 at1A47 toggles the next tactic element instead of the selected one')
PORTS.variant('speed-right-increments', '9372 at9413 increments the match delay byte instead of decrementing it')
PORTS.variant('menu-tactics-wrong-country', 'ED8A atEFE3 passes country+1 to the tactics editor instead of the selected country')
PORTS.variant('tactics-change-unflagged', 'ED8A atF004 omits the changed-tactics refresh flag DS:9B55')
M16 = 0xFFFF


def _g(mem, r, target, *args, ret, far=True):
    """A library/menu guest call whose unqualified target/return lives in 214B."""
    return (yield from guest(mem, r, target if ':' in target else '214B:'+target,
                             *args, ret=ret if ':' in ret else '214B:'+ret, far=far))


def _wd8(mem, off, value, at):
    mem.wds8(off, value, at)


def _ret_site(mem):
    sp, far = mem._entries[-1]
    return f"{(mem.u16(mem.ss_lin(sp+2))-getattr(mem,'m',mem).load)&M16:04X}:{mem.u16(mem.ss_lin(sp)):04X}"


@PORTS.port('214B:0723', ret='retf')
def key_pressed(mem, variant):
    # The unhooked kit returns at this exact entry, without the BIOS frame.
    has = mem.keypressed(_ret_site(mem))
    mem.set_reg('ax', (mem.reg('ax') & 0xFF00) | int(has))


@PORTS.port('214B:08DD', ret='retf')
def read_key(mem, variant):
    # Match preflights decisions in the entry hook, before this Python body runs.
    # Only the pushed-back-key path executes the original's frame in the kit.
    if mem.ds8(0x79AE):
        r = Regs(mem); r.enter(0x14)
        mem.wds8(0x79AE, 0, '214B:08EA')
        r.al = mem.ds8(0xA976)
        mem.wds8(0xA977, r.al, '214B:097C')
        return _end(r)
    mem.read_key(_ret_site(mem))


@PORTS.port('214B:0993', ret='retf 2')
def push_back_key(mem, variant):
    r = Regs(mem); r.enter()
    mem.wds8(0x79AE, 1, '214B:0996')
    r.al = ss8(mem, r, r.bp+6)
    mem.wds8(0xA976, r.al, '214B:099E')
    return _end(r)


@PORTS.port('214B:0983', ret='retf')
def wait_key_clear(mem, variant):
    r = Regs(mem); r.enter()
    r = yield from _g(mem, r, '08DD', ret='098A')
    mem.wds8(0xA976, 0, '214B:098A')
    return _end(r)


def _clamp(mem, word):
    r = Regs(mem); r.enter()
    r.al = mem.ds8(0xA976)
    key = r.al
    base = '14AC' if word else '13F6'
    get = rw if word else rb
    put = w16 if word else w8
    if key in (0xAD, 0xAB):
        farg(mem,r,8)
        put(mem,r,0,1,'214B:'+('14BD' if word else '1407'))
    elif key in (0xB2,0xB0):
        if word: r.ax = ss16(mem,r,r.bp+6)
        else: r.al = ss8(mem,r,r.bp+6)
        farg(mem,r,8)
        put(mem,r,0,r.ax if word else r.al,'214B:'+('14D2' if word else '141B'))
    elif key == 0xAC:
        farg(mem,r,8)
        if get(mem,r,0)>1:
            farg(mem,r,8)
            put(mem,r,0,get(mem,r,0)-1,'214B:'+('14E7' if word else '1430'))
    elif key == 0xB1:
        farg(mem,r,8)
        if word:r.ax=get(mem,r,0)
        else:r.al=get(mem,r,0);r.ah=0
        if r.ax<ss16(mem,r,r.bp+6):
            farg(mem,r,8)
            put(mem,r,0,get(mem,r,0)+1,'214B:'+('14FE' if word else '1449'))
    return _end(r)


@PORTS.port('214B:13F6', ret='retf 6')
def move_byte_clamp(mem, variant):
    return _clamp(mem,False)


@PORTS.port('214B:14AC', ret='retf 6')
def move_word_clamp(mem, variant):
    return _clamp(mem,True)


def _wrap(mem,word):
    r=Regs(mem);r.enter()
    r.al=mem.ds8(0xA976)
    key=r.al
    get=rw if word else rb
    put=w16 if word else w8
    if key==0xAC:
        farg(mem,r,8)
        if get(mem,r,0)>1:
            farg(mem,r,8)
            put(mem,r,0,get(mem,r,0)-1,'214B:'+('151D' if word else '1468'))
        else:
            if word:r.ax=ss16(mem,r,r.bp+6)
            else:r.al=ss8(mem,r,r.bp+6)
            farg(mem,r,8)
            put(mem,r,0,r.ax if word else r.al,'214B:'+('1528' if word else '1473'))
    elif key==0xB1:
        farg(mem,r,8)
        if word:r.ax=get(mem,r,0)
        else:r.al=get(mem,r,0);r.ah=0
        if r.ax<ss16(mem,r,r.bp+6):
            farg(mem,r,8)
            put(mem,r,0,get(mem,r,0)+1,'214B:'+('153F' if word else '148C'))
        else:
            farg(mem,r,8)
            put(mem,r,0,1,'214B:'+('1547' if word else '1494'))
    else:
        farg(mem,r,8)
        r=yield from _g(mem,r,'14AC' if word else '13F6',r.es,r.di,ss16(mem,r,r.bp+6),
                        ret='155A' if word else '14A6')
    return _end(r)


@PORTS.port('214B:1452', ret='retf 6')
def move_byte_wrap(mem,variant):
    return (yield from _wrap(mem,False))


@PORTS.port('214B:1507', ret='retf 6')
def move_word_wrap(mem,variant):
    return (yield from _wrap(mem,True))


@PORTS.port('214B:1560', ret='retf 6')
def menu_read_move(mem,variant):
    r=Regs(mem);r.enter()
    r.di,r.es=mem.ds16(0xA96E),mem.ds16(0xA970)
    source=r.es,r.di
    r.di,r.es=mem.ds16(0xA96A),mem.ds16(0xA96C)
    r.ax=4000
    r=yield from _g(mem,r,'23E4:025D',*source,r.es,r.di,r.ax,ret='1578')
    r=yield from _g(mem,r,'08DD',ret='157C')
    farg(mem,r,8)
    r=yield from _g(mem,r,'1507',r.es,r.di,ss16(mem,r,r.bp+6),ret='1588')
    return _end(r)


@PORTS.port('1771:4925',ret='ret 4')
def next_position(mem,variant):
    r=Regs(mem);r.enter()
    mem.wds8(0xA976,0xB1,'1771:4928')
    farg(mem,r,4);w8(mem,r,0,rb(mem,r,0)+1,'1771:4930')
    farg(mem,r,4);r.ax=14
    r=yield from _g(mem,r,'1452',r.es,r.di,r.ax,ret='1771:4941')
    farg(mem,r,4);w8(mem,r,0,rb(mem,r,0)-1,'1771:4944')
    mem.wds8(0xA976,0,'1771:4947')
    return _end(r)


@PORTS.port('1771:4952',ret='retf 2')
def edit_position(mem,variant):
    r=Regs(mem);r.enter(4)
    word=ss16(mem,r,r.bp+6)
    player_of(mem,r,word)
    r.local16(-4,r.di);r.local16(-2,r.es)
    if word:
        r.al=mem.ds8(0xA976)
        r=yield from _g(mem,r,'23E4:19B2',r.ax,ret='1771:497B')
        if r.al==ord('C'):
            farg(mem,r,-4);r.al=rb(mem,r,7)
            farg(mem,r,-4);w8(mem,r,6,r.al,'1771:4989')
        else:
            farg(mem,r,-4);r.di=r.di+6
            r=yield from _g(mem,r,'1771:4925',r.es,r.di,ret='1771:499B',far=False)
        if mem.ds8(0x0C1F):mem.wds8(0x9B55,1,'1771:49A2')
        if mem.ds8(0x0C1E):
            r=yield from _g(mem,r,'1771:3EF8',ret='1771:49B2')
    return _end(r)


@PORTS.port('0791:92FC',ret='ret 2')
def switch_to_quick(mem,variant):
    r=Regs(mem);r.enter()
    if not mem.ds8(0x9A3E) and mem.ds16(0x831B) and not mem.ds8(0x8326) and not mem.ds8(0x0C21):
        if not mem.ds8(0x8325) or any(mem.ds8(k) for k in (0x0C20,0x7C37,0x9B55)):
            if not mem.ds8(0x7C38):
                r.di=0xA96A
                r=yield from guest(mem,r,'214B:0329',mem.DS,0x26E4,mem.DS,r.di,ret='934F')
            mem.wds8(0x7C38,1,'0791:934F')
        else:
            mem.wds8(0x9A3E,1,'0791:9356')
            mem.wds8(0x9A3F,1,'0791:935B')
            mem.wds8(0x7C38,0,'0791:9360')
            r.al=0
            r=yield from guest(mem,r,'0106',r.ax,ret='936C')
    return _end(r)


@PORTS.port('0791:9372',ret='ret')
def match_key_poll(mem,variant):
    r=Regs(mem);r.enter(2)
    r.local16(-2,1)
    for slot in range(1,7):
        if slot>1:r.local16(-2,slot)
        r.di,r.es=mem.ds16(0xA923),mem.ds16(0xA925)
        r.al=rb(mem,r,0x3F);r.ah=0
        r.dx=r.ax;r.ax=6-r.dx
        r.al=int(r.ax>=slot);cbw(r)
        r.di=r.ax
        r.dx=(r.dx&0xFF00)|mem.ds8((r.di+0x882)&M16)
        r.ax=(slot+0x795)<<1
        r.di,r.es=mem.ds16(0x7C26),mem.ds16(0x7C28)
        r.di=r.di+r.ax
        w8(mem,r,-2,r.dx&0xFF,'93B3')
    r=yield from guest(mem,r,'214B:0723',ret='93C2')
    if r.al:
        r=yield from guest(mem,r,'214B:1E8D',ret='93CE')
        r=yield from guest(mem,r,'214B:08DD',ret='93D3')
        r.al=mem.ds8(0xA976)
        r=yield from guest(mem,r,'23E4:19B2',r.ax,ret='93DC')
        key=r.al
        if key==0x20:
            r=yield from guest(mem,r,'1A04',ret='93E3',far=False)
        elif key in (0xAE,0xAF):
            r.di,r.es=mem.ds16(0xA923),mem.ds16(0xA925)
            speed=rb(mem,r,0x3F)
            if key==0xAE and speed<5:
                r.di,r.es=mem.ds16(0xA923),mem.ds16(0xA925)
                w8(mem,r,0x3F,speed+1,'93F9')
            elif key==0xAF and speed>0:
                r.di,r.es=mem.ds16(0xA923),mem.ds16(0xA925)
                w8(mem,r,0x3F,speed+1 if variant=='speed-right-increments' else speed-1,'9413')
        elif key in (0xAC,0xB1):
            r.di=0x66A
            r.al=0;lo=r.ax
            r.al=4;hi=r.ax
            r.al=int(mem.ds8(0xA976)==0xB1);cbw(r);r.di=r.ax
            r.al=mem.ds8((r.di+0x7920)&M16);cbw(r)
            r=yield from guest(mem,r,'214B:1D6F',mem.DS,0x66A,lo,hi,r.ax,ret='9448')
            r=yield from guest(mem,r,'0691',ret='944B',far=False)
        elif key in (0x0D,0x1B):
            r.al=1
            r=yield from guest(mem,r,'ED8A',r.ax,ret='945B',far=False)
        elif key==0x9F:
            if not mem.ds8(0x9A3E):
                r.di,r.es=mem.ds16(0xA96A),mem.ds16(0xA96C);source=r.es,r.di
                r.di,r.es=mem.ds16(0xA972),mem.ds16(0xA974);r.ax=4000
                r=yield from guest(mem,r,'23E4:025D',*source,r.es,r.di,r.ax,ret='947D')
                r=yield from guest(mem,r,'16D6:0945',ret='9482')
                r.di,r.es=mem.ds16(0xA972),mem.ds16(0xA974);source=r.es,r.di
                r.di,r.es=mem.ds16(0xA96A),mem.ds16(0xA96C);r.ax=4000
                r=yield from guest(mem,r,'23E4:025D',*source,r.es,r.di,r.ax,ret='9497')
        elif key==0xA7:
            r=yield from guest(mem,r,'214B:1E5A',ret='94A2')
        elif key==ord('R'):
            r=yield from guest(mem,r,'92FC',r.bp,ret='94AC',far=False)
    elif mem.ds8(0x7C38):
        r=yield from guest(mem,r,'92FC',r.bp,ret='94B9',far=False)
    if mem.ds8(0x9A3E):
        r=yield from guest(mem,r,'214B:1E8D',ret='94C5')
    return _end(r)


@PORTS.port('0791:7FCF',ret='ret 4')
def timed_notice(mem,variant):
    r=Regs(mem);r.enter()
    r=yield from guest(mem,r,'214B:0625',ret='7FD7')
    keeper=ss8(mem,r,r.bp+6)
    r.di=0xA96E
    r=yield from guest(mem,r,'214B:0329',mem.DS,0x5B66 if keeper else 0x5B30,mem.DS,r.di,ret='7FFD' if keeper else '7FEC')
    if keeper:
        r.al=ss8(mem,r,r.bp+4);cbw(r);r.di=r.ax<<1
        side=mem.ds16((r.di+0x9B34)&M16)
        r.ax=1
        r=yield from guest(mem,r,'1771:0F58',side,25,r.ax,ret='8016')
    r.di,r.es=mem.ds16(0xA96E),mem.ds16(0xA970);r.di=r.di+0xF00;source=r.es,r.di
    r.di,r.es=mem.ds16(0xA96A),mem.ds16(0xA96C);r.di=r.di+0xF00;r.ax=0xA0
    r=yield from guest(mem,r,'214B:003C',*source,r.es,r.di,r.ax,ret='8033')
    r.al=ss8(mem,r,r.bp+6);cbw(r);r.di=r.ax<<1
    r=yield from guest(mem,r,'CC2E',mem.ds16((r.di+0x87C)&M16),ret='8042',far=False)
    r=yield from guest(mem,r,'214B:0723',ret='8047')
    if r.al:r=yield from guest(mem,r,'214B:08DD',ret='8050')
    else:mem.wds8(0xA977,0x1B,'0791:8052')
    r=yield from guest(mem,r,'214B:0643',ret='805C')
    return _end(r)


@PORTS.port('1771:1981',ret='retf 2')
def edit_team_tactics(mem,variant):
    r=Regs(mem);r.enter(6)
    country=ss16(mem,r,r.bp+6)
    squad_of(mem,r,country);r.local16(-5,r.di);r.local16(-3,r.es)
    r.al=0
    r=yield from _g(mem,r,'1771:0B77',country,ret='1771:19A8')
    r.al=int(bool(r.al) and not mem.ds8(0x0C20));r.local8(-1,r.al)
    editable=bool(r.al)
    r.di=0xA96E
    r=yield from _g(mem,r,'0329',mem.DS,0x1E0C if editable else 0x14A6,mem.DS,r.di,
                    ret='1771:19D1' if editable else '1771:19E2')
    while True:
        r=yield from _g(mem,r,'1771:157D',country,ret='1771:19E8',far=False)
        if editable:
            r.al=int(mem.ds16(0xD8E)>3);cbw(r);r.di=r.ax
            r.al=mem.ds8((r.di+0xD90)&M16);r.ah=0;r.ax=r.ax+mem.ds16(0xD8E)
            row=r.ax;r.ax=0x1A
            r=yield from _g(mem,r,'13C5',row,0x24,r.ax,ret='1771:1A16')
        r.di=0xD8E;r.ax=8
        r=yield from _g(mem,r,'1560',mem.DS,r.di,r.ax,ret='1771:1A24')
        if not editable:break
        if mem.ds8(0xA976)==0x0D:
            r.di=mem.ds16(0xD8E);r.al=mem.ds8((r.di+0x6BBF)&M16);r.ah=0
            element=(r.ax%8)+1 if variant=='tactics-adjacent-bit' else r.ax
            farg(mem,r,-5);r.di=r.di+0x2D
            r=yield from _g(mem,r,'0CF4',element,r.es,r.di,ret='1771:1A4C')
        r.al=1
        if mem.ds8(0x0C1E):
            r.di=mem.ds16(0xD8E)
            if mem.ds8((r.di+0x6BBF)&M16)==8:
                r=yield from _g(mem,r,'1771:3EF8',ret='1771:1A68')
        if mem.ds8(0xA976)==0x1B:
            mem.wds8(0xC1A,1,'1771:1A72');break
    return _end(r)


@PORTS.port('0791:ED8A',ret='ret 2')
def in_match_menu(mem,variant):
    r=Regs(mem);r.enter(0x10)
    if ss8(mem,r,r.bp+4):
        r.di,r.es=mem.ds16(0xA96A),mem.ds16(0xA96C);source=r.es,r.di
        r.di,r.es=mem.ds16(0xA972),mem.ds16(0xA974);r.ax=4000
        r=yield from guest(mem,r,'23E4:025D',*source,r.es,r.di,r.ax,ret='EDAB')
    r=yield from guest(mem,r,'230C',ret='EDAE',far=False)
    r=yield from guest(mem,r,'1771:0B77',mem.ds16(0x9B36),ret='EDB7')
    if r.al:r.local8(-2,1)
    else:
        r=yield from guest(mem,r,'1771:0B77',mem.ds16(0x9B34),ret='EDCA')
        r.local8(-2,0 if r.al else 1)
    r.al=ss8(mem,r,r.bp-2);cbw(r);r.di=r.ax
    r.al=mem.ds8((r.di+0xAC2)&M16);r.ah=0;r.local16(-7,r.ax)
    while True:
        r.al=ss8(mem,r,r.bp-7);element=r.ax;r.di=0xED37
        r=yield from guest(mem,r,'23E4:08DF',element,mem.seg(0x0791),r.di,ret='EDF5')
        if not member(mem):
            r.al=int(ss16(mem,r,r.bp-7)<6);r.local8(-2,r.al)
        r.al=ss8(mem,r,r.bp-2);cbw(r);r.di=r.ax<<1
        r.ax=mem.ds16((r.di+0x9B34)&M16);r.local16(-5,r.ax)
        r=yield from guest(mem,r,'A75D',ret='EE18',far=False)
        if mem.ds8(0x066D):
            r.al=7;colour=r.ax;r.di=0xED57;source=mem.seg(0x0791),r.di
            r.al=0x14;row=r.ax;r.al=0x27;col=r.ax;r.di=0xA96E
            r=yield from guest(mem,r,'214B:02C8',colour,*source,row,col,mem.DS,r.di,ret='EE37')
        r.di=0xA96E
        r=yield from guest(mem,r,'214B:0329',mem.DS,0x2598,mem.DS,r.di,ret='EE46')
        args=[]
        for off in (0xACD,0xAD7,0xAE1):
            r.di=ss16(mem,r,r.bp-7);r.al=mem.ds8((r.di+off)&M16);r.ah=0;args.append(r.ax)
        r=yield from guest(mem,r,'214B:13C5',*args,ret='EE69')
        r.al=7;colour=r.ax
        r.di,r.es=mem.ds16(0xA923),mem.ds16(0xA925);r.al=rb(mem,r,0x41);cbw(r)
        r.di=(r.ax<<2)+0xAC6;source=mem.DS,r.di
        r.al=0x19;row=r.ax;r.al=0x3D;col=r.ax;r.di=0xA96E
        r=yield from guest(mem,r,'214B:02C8',colour,*source,row,col,mem.DS,r.di,ret='EE91')
        r.di=r.bp-7;r.ax=10
        r=yield from guest(mem,r,'214B:1560',r.ss,r.di,r.ax,ret='EE9F')
        r.al=int(mem.ds8(0xA976)==0x1B and bool(mem.ds8(0xC1F)));r.local8(-1,r.al)
        r.al=mem.ds8(0xA976);key=r.al
        if key in (0xAB,0xB0):
            r=yield from guest(mem,r,'1771:0B77',mem.ds16(0x9B36),ret='EEC6' if key==0xAB else 'EEE2')
            cbw(r);r.di=r.ax;r.al=mem.ds8((r.di+(0xAC4 if key==0xAB else 0xAC2))&M16)
            r.ah=0;r.local16(-7,r.ax)
        elif key in (0xAE,0xAF):
            r.al=ss8(mem,r,r.bp-7);element=r.ax;r.di=0xED5C
            r=yield from guest(mem,r,'23E4:08DF',element,mem.seg(0x0791),r.di,ret='EF07')
            if member(mem):
                r.al=int(ss16(mem,r,r.bp-7)<6);cbw(r);r.di=r.ax
                r.al=mem.ds8((r.di+0x7920)&M16);cbw(r);r.cx=5;imul(r,r.cx)
                r.local16(-7,ss16(mem,r,r.bp-7)+r.ax)
            else:
                r.al=int(mem.ds8(0xA976)==0xAE);cbw(r);r.di=r.ax
                r.al=mem.ds8((r.di+0xAC4)&M16);r.ah=0;r.local16(-7,r.ax)
        elif key==0xB6:
            r.di,r.es=mem.ds16(0xA923),mem.ds16(0xA925)
            r.local16(-15,r.di);r.local16(-13,r.es)
            farg(mem,r,-15);r.al=int(rb(mem,r,0x41)==0)
            farg(mem,r,-15);w8(mem,r,0x41,r.al,'EF63')
        elif key==0x20:
            r=yield from guest(mem,r,'E949',r.bp,ret='EF71',far=False)
        if mem.ds8(0xA976)==0x0D:
            r.ax=ss16(mem,r,r.bp-7);item=r.ax
            if item in (1,6):
                r.di=0xA96E
                r=yield from guest(mem,r,'214B:0329',mem.DS,0x1E4C,mem.DS,r.di,ret='EF9A')
                r=yield from guest(mem,r,'1771:0B77',ss16(mem,r,r.bp-5),ret='EFA2')
                if r.al and not mem.ds8(0xC20):
                    r.di=0xA96E
                    r=yield from guest(mem,r,'214B:0329',mem.DS,0x1EB4,mem.DS,r.di,ret='EFBC')
                r.ax=0x40
                r=yield from guest(mem,r,'1771:0F58',ss16(mem,r,r.bp-5),9,r.ax,ret='EFCC')
                squad_of(mem,r,ss16(mem,r,r.bp-5));r.al=rb(mem,r,0x2D);r.ah=0;r.local16(-11,r.ax)
                country=ss16(mem,r,r.bp-5)
                if variant=='menu-tactics-wrong-country':country=(country+1)&M16
                r=yield from guest(mem,r,'1771:1981',country,ret='EFEB')
                squad_of(mem,r,ss16(mem,r,r.bp-5));r.al=rb(mem,r,0x2D);r.ah=0
                if r.ax!=ss16(mem,r,r.bp-11) and variant!='tactics-change-unflagged':
                    mem.wds8(0x9B55,1,'0791:F004')
            elif item in (2,7):
                r=yield from guest(mem,r,'E949',r.bp,ret='F019',far=False)
            elif item in (4,9):
                r.al=1;r=yield from guest(mem,r,'0106',r.ax,ret='F02C')
            elif item in (3,8):
                r.al=mem.ds8(0xC21);flag=r.ax;r.di=0xED7C
                r=yield from guest(mem,r,'214B:1765',flag,mem.seg(0x0791),r.di,ret='F046')
                if not r.al:
                    country=ss16(mem,r,r.bp-5);r.al=1
                    r=yield from guest(mem,r,'E929',country,r.ax,ret='F054')
            else:r.local8(-1,1)
        if not ss8(mem,r,r.bp-1):continue
        r=yield from guest(mem,r,'EA09',r.bp,ret='F067',far=False)
        if r.al:break
    if mem.ds8(0xC1F):
        r.di,r.es=mem.ds16(0xA972),mem.ds16(0xA974);source=r.es,r.di
        r.di,r.es=mem.ds16(0xA96A),mem.ds16(0xA96C);r.ax=4000
        r=yield from guest(mem,r,'23E4:025D',*source,r.es,r.di,r.ax,ret='F08A')
    mem.wds8(0xC1F,1,'0791:F08A')
    r=yield from guest(mem,r,'230C',ret='F092',far=False)
    return _end(r)


@PORTS.port('1771:4B61',ret='retf 4')
def edit_own_tactics(mem,variant):
    r=Regs(mem);r.enter(6)
    word=ss16(mem,r,r.bp+8)
    player_of(mem,r,word);r.local16(-5,r.di);r.local16(-3,r.es)
    if not word:return _end(r)
    r.di=0xA96E
    r=yield from _g(mem,r,'0329',mem.DS,0x46C6,mem.DS,r.di,ret='1771:4B93')
    can=False
    if mem.ds8(0xC1E):
        player_of(mem,r,word)
        if rb(mem,r,6)>1 and ss8(mem,r,r.bp+6):
            r=yield from _g(mem,r,'1771:3216',word,ret='1771:4BBC')
            can=not bool(r.al)
    r.al=int(can);r.local8(-1,r.al)
    if mem.ds16(0xF38)==5 and not can:mem.wds16(0xF38,1,'1771:4BD6')
    while True:
        r=yield from _g(mem,r,'1771:42BC',word,ret='1771:4BE3')
        r.ax=mem.ds16(0xF38)+11;row=r.ax;r.ax=0x18
        r=yield from _g(mem,r,'13C5',row,0x26,r.ax,ret='1771:4BF7')
        r.di=0xF38;r.al=ss8(mem,r,r.bp-1);r.ah=0;r.ax=r.ax+4
        r=yield from _g(mem,r,'1560',mem.DS,r.di,r.ax,ret='1771:4C0A')
        if mem.ds8(0xA976)==0x0D:
            if mem.ds8(0xC1F):mem.wds8(0x9B55,1,'1771:4C1B')
            if mem.ds16(0xF38)==5:
                r=yield from _g(mem,r,'1771:49B8',r.bp,ret='1771:4C2B',far=False)
            else:
                r.ax=mem.ds16(0xF38)+4;element=r.ax
                farg(mem,r,-5);r.al=rb(mem,r,15);r.ah=0
                r=yield from _g(mem,r,'0C57',element,r.ax,ret='1771:4C44')
                if not r.al:
                    r.ax=mem.ds16(0xF38)+4;element=r.ax
                    farg(mem,r,-5);r.di=r.di+15
                    r=yield from _g(mem,r,'0C79',element,r.es,r.di,ret='1771:4C5D')
                    element=mem.ds16(0xF38);farg(mem,r,-5);r.di=r.di+15
                    r=yield from _g(mem,r,'0CA1',element,r.es,r.di,ret='1771:4C6F')
                else:
                    element=mem.ds16(0xF38);farg(mem,r,-5);r.al=rb(mem,r,15);r.ah=0
                    r=yield from _g(mem,r,'0C57',element,r.ax,ret='1771:4C84')
                    if not r.al:
                        element=mem.ds16(0xF38);farg(mem,r,-5);r.di=r.di+15
                        r=yield from _g(mem,r,'0C79',element,r.es,r.di,ret='1771:4C9A')
                    else:
                        r.ax=mem.ds16(0xF38)+4;element=r.ax
                        farg(mem,r,-5);r.di=r.di+15
                        r=yield from _g(mem,r,'0CA1',element,r.es,r.di,ret='1771:4CB1')
                        # 4CB1..4CE2 holds the assignment target across the set-test call.
                        r.push(mem.ds16(0xF38));farg(mem,r,-5);r.di=r.di+15
                        r.push(r.es);r.push(r.di)
                        element=mem.ds16(0xF38);farg(mem,r,-5);r.al=rb(mem,r,0);r.ah=0
                        r.dx=0xBF;mul(r,r.dx)
                        r.di,r.es=mem.ds16(0xA917),mem.ds16(0xA919);r.di=r.di+r.ax
                        r.al=rb(mem,r,0x2D);r.ah=0
                        r=yield from _g(mem,r,'0C57',element,r.ax,ret='1771:4CE1')
                        # Already-held three words become the first arguments.
                        value=r.ax
                        r.sp=r.sp+6
                        farg(mem,r,-5);r.di=r.di+15
                        r=yield from _g(mem,r,'0CCB',mem.ds16(0xF38),r.es,r.di,value,ret='1771:4CE7')
        if mem.ds8(0xA976)==0x1B:break
    return _end(r)


@PORTS.port('1771:49B8',ret='ret 2')
def cycle_marking(mem,variant):
    r=Regs(mem);r.enter(12)
    r.di=ss16(mem,r,r.bp+4);word=ss16(mem,r,r.di+8)
    player_of(mem,r,word);r.local16(-11,r.di);r.local16(-9,r.es)
    farg(mem,r,-11);r.al=rb(mem,r,0);r.ah=0
    second=r.ax==mem.ds16(0x9B36);r.local8(-1,int(second))
    r.di=ss16(mem,r,r.bp+4);word=ss16(mem,r,r.di+8)
    farg(mem,r,-11);r.al=rb(mem,r,0);r.ah=0
    r=yield from _g(mem,r,'1771:3A82',word,r.ax,ret='1771:4A02')
    slot=r.ax;r.local16(-7,slot)
    r.al=int(not second);cbw(r);r.di=r.ax<<1
    r.ax=mem.ds16((r.di+0x9B34)&M16);other=r.ax;r.local16(-5,other)
    farg(mem,r,-11)
    if rb(mem,r,6)<2:
        r.ax=7;farg(mem,r,-11);r.di=r.di+16
        r=yield from _g(mem,r,'0CA1',r.ax,r.es,r.di,ret='1771:4A39')
    else:
        r.ax=7;element=r.ax;farg(mem,r,-11);r.al=rb(mem,r,16);r.ah=0
        r=yield from _g(mem,r,'0C57',element,r.ax,ret='1771:4A4F')
        if r.al:
            index=12;r.local16(-3,index)
            while True:
                index=(index-1)&M16;r.local16(-3,index)
                if index==1:break
                r.ax=index<<1;r.cx=r.ax
                squad_of(mem,r,other);r.di=r.di+r.cx;r.bx=rw(mem,r,-2)
                r.ax=slot<<1;r.cx=r.ax;r.al=int(second);cbw(r);r.dx=0x28;mul(r,r.dx)
                r.di=r.ax+r.cx;r.ax=mem.ds16((r.di+0x9A3E)&M16)
                if r.ax==r.bx:break
        else:r.ax=0;index=0;r.local16(-3,0)
        while True:
            index=(index+1)&M16;r.local16(-3,index)
            if index>11:r.ax=0;index=0;r.local16(-3,0)
            if index<2:break
            r.ax=index<<1;r.cx=r.ax
            squad_of(mem,r,other);r.di=r.di+r.cx
            r=yield from _g(mem,r,'1771:3216',rw(mem,r,-2),ret='1771:4AD2')
            if not r.al:break
        r.ax=7;farg(mem,r,-11);r.di=r.di+16
        r=yield from _g(mem,r,'0C79' if index else '0CA1',r.ax,r.es,r.di,
                        ret='1771:4B02' if index else '1771:4AEE')
        if index>1:
            r.ax=index<<1;r.cx=r.ax
            squad_of(mem,r,other);r.di=r.di+r.cx;r.bx=rw(mem,r,-2)
            r.ax=slot<<1;r.cx=r.ax;r.al=int(second);cbw(r);r.dx=0x28;mul(r,r.dx)
            r.di=r.ax+r.cx
            mem.wds16((r.di+0x9A3E)&M16,r.bx,'1771:4B37')
        else:
            r.ax=slot<<1;r.cx=r.ax;r.al=int(second);cbw(r);r.dx=0x28;mul(r,r.dx)
            r.di=r.ax+r.cx;r.ax=0
            mem.wds16((r.di+0x9A3E)&M16,r.ax,'1771:4B53')
    r=yield from _g(mem,r,'1771:3EF8',ret='1771:4B5B')
    return _end(r)


@PORTS.port('214B:1765',ret='retf 6')
def message_if_flag(mem,variant):
    r=Regs(mem);r.enter(0x52)
    source=farg(mem,r,6)
    r.di=r.bp-0x52;temporary=r.di;r.ax=80
    r=yield from _g(mem,r,'23E4:0644',*source,r.ss,temporary,r.ax,ret='177E')
    r.al=ss8(mem,r,r.bp+10);r.local8(-1,r.al)
    if ss8(mem,r,r.bp+10):
        r.di=r.bp-0x52
        r=yield from _g(mem,r,'04F8',r.ss,r.di,ret='1793')
    r.al=ss8(mem,r,r.bp-1)
    return _end(r)


@PORTS.port('214B:04F8',ret='retf 4')
def message_wait_key(mem,variant):
    r=Regs(mem);r.enter(0x154)
    source=farg(mem,r,6)
    r.di=r.bp-0x51;line=r.di;r.ax=80
    r=yield from _g(mem,r,'23E4:0644',*source,r.ss,line,r.ax,ret='0512')
    r.al=mem.ds8(0x7922);r.ah=0;r.local16(-0x53,r.ax)
    r.al=mem.ds8(0x7924);mem.wds8(0x7922,r.al,'214B:051D')
    r=yield from _g(mem,r,'0625',ret='0524')
    r.al=25;row=r.ax;r.push(row)
    r.di=r.bp-0x153;expression=r.di;r.push(r.ss);r.push(r.di)
    r.di=line
    r=yield from _g(mem,r,'23E4:062A',r.ss,r.di,ret='0537')
    r.di=0x4E7
    r=yield from _g(mem,r,'23E4:06B7',mem.seg(0x214B),r.di,ret='0541')
    r.di=0xA96A
    r.sp=r.sp+6
    r=yield from _g(mem,r,'0350',row,r.ss,expression,mem.DS,r.di,ret='054A')
    r=yield from _g(mem,r,'0983',ret='054E')
    r=yield from _g(mem,r,'0643',ret='0552')
    r.al=ss8(mem,r,r.bp-0x53);mem.wds8(0x7922,r.al,'214B:0555')
    return _end(r)


@PORTS.port('214B:0566',ret='retf 4')
def ask_yes_no(mem,variant):
    r=Regs(mem);r.enter(0x152)
    source=farg(mem,r,6)
    r.di=r.bp-0x52;line=r.di;r.ax=80
    r=yield from _g(mem,r,'23E4:0644',*source,r.ss,line,r.ax,ret='0580')
    r=yield from _g(mem,r,'0625',ret='0584')
    r.al=25;row=r.ax;r.push(row)
    r.di=r.bp-0x152;expression=r.di;r.push(r.ss);r.push(r.di)
    r.di=line
    r=yield from _g(mem,r,'23E4:062A',r.ss,r.di,ret='0597')
    r.di=0x55E
    r=yield from _g(mem,r,'23E4:06B7',mem.seg(0x214B),r.di,ret='05A1')
    r.di=0xA96A
    r.sp=r.sp+6
    r=yield from _g(mem,r,'0350',row,r.ss,expression,mem.DS,r.di,ret='05AA')
    r.di=0x7946
    r=yield from _g(mem,r,'09A7',mem.DS,r.di,ret='05B3')
    r.al=mem.ds8(0xA976)
    r=yield from _g(mem,r,'23E4:19B2',r.ax,ret='05BC')
    r.al=int(r.al==ord('Y'));r.local8(-1,r.al)
    r=yield from _g(mem,r,'0643',ret='05CD')
    mem.wds8(0xA976,0,'214B:05CD')
    r.al=ss8(mem,r,r.bp-1)
    return _end(r)


@PORTS.port('214B:09A7',ret='retf 4')
def wait_key_in_set(mem,variant):
    r=Regs(mem);r.enter(0x20)
    source=farg(mem,r,6)
    r.di=r.bp-0x20;target=r.di;r.ax=0x20
    r=yield from _g(mem,r,'23E4:08BF',*source,r.ss,target,r.ax,ret='09C0')
    while True:
        r=yield from _g(mem,r,'08DD',ret='09C4')
        r.al=mem.ds8(0xA976);element=r.ax;r.di=r.bp-0x20
        r=yield from _g(mem,r,'23E4:08DF',element,r.ss,r.di,ret='09D2')
        if member(mem):break
    return _end(r)


@PORTS.port('214B:158E',ret='ret 6')
def set_list_pair(mem,variant):
    r=Regs(mem);r.enter()
    r.ax=ss16(mem,r,r.bp+8)
    r.di=ss16(mem,r,r.bp+4)
    parent=r.di
    r.di,r.es=ss16(mem,r,parent+14),ss16(mem,r,parent+16)
    w16(mem,r,0,r.ax,'214B:159B')
    r.ax=ss16(mem,r,r.bp+6)
    r.di=ss16(mem,r,r.bp+4)
    parent=r.di
    r.di,r.es=ss16(mem,r,parent+10),ss16(mem,r,parent+12)
    w16(mem,r,0,r.ax,'214B:15A8')
    return _end(r)


@PORTS.port('1771:4859',ret='retf 6')
def edit_player_name(mem,variant):
    r=Regs(mem);r.enter(0x10E)
    word=ss16(mem,r,r.bp+10)
    if word:
        r.di=r.bp-0x10D;expression=r.di;r.push(r.ss);r.push(r.di)
        r=yield from _g(mem,r,'1771:2E93',word,ret='1771:4876')
        r.di=r.bp-13;name=r.di;r.ax=12;r.sp=r.sp+4
        r=yield from _g(mem,r,'23E4:0644',r.ss,expression,r.ss,name,r.ax,ret='1771:4884')
        r.di=name;ptr=r.ss,r.di;r.al=12;maximum=r.ax
        r.al=ss8(mem,r,r.bp+6);left=r.ax
        r.ax=ss16(mem,r,r.bp+6)+12;right=r.ax
        r.al=ss8(mem,r,r.bp+8)
        r=yield from _g(mem,r,'1086',*ptr,maximum,left,right,r.ax,ret='1771:48A0')
        r.di=name;r.push(r.ss);r.push(r.di)
        r.di=expression;r.push(r.ss);r.push(r.di)
        r=yield from _g(mem,r,'1771:2E93',word,ret='1771:48B2')
        # Name result and the held comparison pointer are the compare arguments.
        r.sp=r.sp+8
        r=yield from _g(mem,r,'23E4:072F',r.ss,name,r.ss,expression,ret='1771:48B7')
        if member(mem):  # string comparison leaves ZF clear for unequal strings
            r.dx=(r.dx&0xFF00)|ss8(mem,r,r.bp-12);r.ax=word
            r.di,r.es=mem.ds16(0x9B70),mem.ds16(0x9B72);r.di=r.di+r.ax
            w8(mem,r,0,r.dx&0xFF,'1771:48C7')
            r.di=name;r.ax=1;index=r.ax
            r.al=int(ss8(mem,r,r.bp-11)==32);r.ah=0;r.ax=r.ax+1
            r=yield from _g(mem,r,'23E4:07DB',r.ss,r.di,index,r.ax,ret='1771:48E8')
            if ss8(mem,r,r.bp-13):
                r.al=ss8(mem,r,r.bp-12)
                r=yield from _g(mem,r,'23E4:19B2',r.ax,ret='1771:48F9')
                r.local8(-12,r.al)
                r.di=name;source=r.ss,r.di;r.ax=word;r.dx=11;mul(r,r.dx)
                r.di,r.es=mem.ds16(0x9B6C),mem.ds16(0x9B6E);r.di=r.di+r.ax;r.ax=10
                r=yield from _g(mem,r,'23E4:0644',*source,r.es,r.di,r.ax,ret='1771:491A')
                mem.wds8(0xC1A,1,'1771:491A')
    return _end(r)


@PORTS.port('214B:15B1',ret='retf 12')
def list_scroll(mem,variant):
    r=Regs(mem);r.enter(2)
    count=ss16(mem,r,r.bp+6);page=ss16(mem,r,r.bp+8)
    farg(mem,r,10);r.ax=rw(mem,r,0);top=r.ax
    farg(mem,r,14);r.ax=r.ax+rw(mem,r,0)-1;position=r.ax
    cursor=rw(mem,r,0);r.local16(-2,position)
    r.al=mem.ds8(0xA976);key=r.al
    pair=None;ret=None
    if key==0xB1:
        r.ax=position
        if r.ax<count:
            farg(mem,r,14);r.ax=rw(mem,r,0)
            if r.ax==page:
                farg(mem,r,14);newcursor=rw(mem,r,0)
                farg(mem,r,10);r.ax=rw(mem,r,0)+1
                pair=newcursor,r.ax;ret='15F3'
            else:
                farg(mem,r,14);r.ax=rw(mem,r,0)+1;newcursor=r.ax
                farg(mem,r,10);pair=newcursor,rw(mem,r,0);ret='1607'
    elif key==0xAC:
        if position>1:
            farg(mem,r,14)
            if rw(mem,r,0)==1:
                farg(mem,r,14);newcursor=rw(mem,r,0)
                farg(mem,r,10);r.ax=rw(mem,r,0)-1
                pair=newcursor,r.ax;ret='162F'
            else:
                farg(mem,r,14);r.ax=rw(mem,r,0)-1;newcursor=r.ax
                farg(mem,r,10);pair=newcursor,rw(mem,r,0);ret='1643'
    elif key==0xAD:
        farg(mem,r,10)
        if rw(mem,r,0)>1:
            r.ax=page+1;farg(mem,r,10)
            if r.ax<=rw(mem,r,0):
                farg(mem,r,14);newcursor=rw(mem,r,0)
                farg(mem,r,10);r.ax=rw(mem,r,0)-page
                pair=newcursor,r.ax;ret='1673'
            else:
                farg(mem,r,14);newcursor=rw(mem,r,0);r.ax=1
                pair=newcursor,r.ax;ret='1683'
        else:
            r.ax=1;newcursor=r.ax;farg(mem,r,10)
            pair=newcursor,rw(mem,r,0);ret='1693'
    elif key==0xB2:
        farg(mem,r,10);r.ax=rw(mem,r,0)+page-1
        if r.ax<count:
            r.ax=(page<<1)&M16;farg(mem,r,10);r.ax=r.ax+rw(mem,r,0)
            if r.ax<=count:
                farg(mem,r,14);newcursor=rw(mem,r,0)
                farg(mem,r,10);r.ax=rw(mem,r,0)+page
                pair=newcursor,r.ax;ret='16CD'
            else:
                farg(mem,r,14);newcursor=rw(mem,r,0);r.ax=count-page+1
                pair=newcursor,r.ax;ret='16E1'
        else:
            r.ax=page;r.dx=0
            r=yield from _g(mem,r,'0D1C',0,count,0,page,ret='16F5')
            newcursor=r.ax;farg(mem,r,10);pair=newcursor,rw(mem,r,0);ret='1700'
    elif key==0xAB:
        r.ax=1;pair=1,1;ret='1712'
    elif key==0xB0:
        r.ax=count;r.dx=0
        r=yield from _g(mem,r,'0D1C',0,page,0,count,ret='172A')
        newcursor=r.ax;r.push(newcursor)
        r.ax=1;r.dx=0;r.push(r.dx);r.push(r.ax)
        r.ax=count;r.dx=0;r.cx=r.ax;r.bx=r.dx
        # 173B..1752 is a signed32-bit count-page+1, without16-bit truncation.
        value=(count-page+1)&0xFFFFFFFF;r.ax=value&M16;r.dx=value>>16
        r=yield from _g(mem,r,'0D56',r.dx,r.ax,ret='175A')
        newtop=r.ax
        # The earlier cursor word remains live across min/max and becomes arg2.
        r.sp=r.sp+2
        pair=newcursor,newtop;ret='175F'
    if pair is not None:
        r=yield from _g(mem,r,'158E',pair[0],pair[1],r.bp,ret=ret,far=False)
    return _end(r)


def _pop(mem,r):
    value=ss16(mem,r,r.sp);r.sp=r.sp+2
    return value


def _dos_interrupt(mem,r):
    """235C:000B..0069: register record -> actual IVT handler -> register record.

    The IRET frame is an existing far guest call with the saved FLAGS as its
    one argument: FLAGS,CS,IP are pushed in that order and all three are consumed
    by IRET. This needs no nested emulation or special guest-frame machinery.
    """
    r.push(r.bp);r.push(mem.reg('ds'));r.bp=r.sp
    initial_bp=r.bp
    saved_flags=mem.reg('eflags')&M16
    r.push(saved_flags);r.bx=0x45;r.push(mem.seg(0x235C));r.push(r.bx)
    r.bx=0
    number=ss8(mem,r,r.bp+12);r.bx=number<<2
    vector_off,vector_seg=mem.farptr(r.bx)
    r.bx=vector_off;r.push(vector_seg);r.push(r.bx)
    off,seg=ss16(mem,r,r.bp+8),ss16(mem,r,r.bp+10)
    r.si=off
    pointer=mem.addr(seg,off)
    values=[mem.u16(pointer+2*k) for k in range(9)]
    r.cld()
    r.ax=values[0];r.si=r.si+2;r.push(r.ax)
    r.ax=values[1];r.si=r.si+2;r.bx=r.ax
    r.ax=values[2];r.si=r.si+2;r.cx=r.ax
    r.ax=values[3];r.si=r.si+2;r.dx=r.ax
    r.ax=values[4];r.si=r.si+2;r.bp=r.ax
    r.ax=values[5];r.si=r.si+2;r.push(r.ax)
    r.ax=values[6];r.si=r.si+2;r.di=r.ax
    r.ax=values[7];r.si=r.si+2;r.push(r.ax)
    r.ax=values[8];r.si=r.si+2;r.es=r.ax
    input_ds=_pop(mem,r);r.si=_pop(mem,r);r.ax=_pop(mem,r)
    # The original retf consumes the temporary vector words. Rebuild only the
    # surviving interrupt frame through guest.call, preserving the dead words.
    r.sp=initial_bp
    r.store(stack=True)
    mem.set_reg('ds',input_ds)
    mem.set_reg('eflags',mem.reg('eflags')&~0x200)  # 0043 CLI
    target=f'{(vector_seg-mem.seg(0))&M16:04X}:{vector_off:04X}'
    from .guest import call
    yield call(target,saved_flags,ret_to='235C:0045',far=True)
    r=Regs(mem,resumed=True)
    # 0045 pushf;0046 push es;0047 push di;0048 push bp;0049 mov bp,sp.
    r.push(mem.reg('eflags')&M16);r.push(r.es);r.push(r.di);r.push(r.bp);r.bp=r.sp
    farg(mem,r,16);r.cld()
    def store(value,at):
        w16(mem,r,0,value,'235C:'+at);r.di=r.di+2
    store(r.ax,'004F')
    r.ax=r.bx;store(r.ax,'0052')
    r.ax=r.cx;store(r.ax,'0055')
    r.ax=r.dx;store(r.ax,'0058')
    r.ax=_pop(mem,r);store(r.ax,'005A')
    r.ax=r.si;store(r.ax,'005D')
    r.ax=_pop(mem,r);store(r.ax,'005F')
    r.ax=mem.reg('ds');store(r.ax,'0062')
    r.ax=_pop(mem,r);store(r.ax,'0064')
    r.ax=_pop(mem,r);store(r.ax,'0066')
    restored_ds=_pop(mem,r);r.bp=_pop(mem,r)
    r.store(stack=True);mem.set_reg('ds',restored_ds)


@PORTS.port('235C:000B',ret='retf 6')
def dos_intr(mem,variant):
    r=Regs(mem)
    yield from _dos_interrupt(mem,r)


@PORTS.port('235C:0000',ret='retf 6',return_stack_delta=-2)
def dos_msdos(mem,variant):
    r=Regs(mem)
    r.si=_pop(mem,r);r.dx=_pop(mem,r);r.cx=_pop(mem,r);r.bx=_pop(mem,r)
    r.al=0x21
    r.push(r.ax);r.push(r.bx);r.push(r.cx);r.push(r.dx);r.push(r.si)
    yield from _dos_interrupt(mem,r)
