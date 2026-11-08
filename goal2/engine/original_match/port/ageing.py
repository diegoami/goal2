"""T124f: original in-season ageing, retirement and replacement.

Read named1771_01/03/06/07 before raw1771_01/05/11/12/13. Each guest call
retains the listing's return PC, full word arguments and near/far frame.
80DA supports stages3/7; its annual2/5 path is deliberately refused BEFORE
any body write. The route must also guard its deferred boundary before70E6,
since stage_end has already changed the stage when it reaches80DA.
"""
from . import Registry
from .mem import PortError,s16
from .runtime import Regs
from .geometry import cbw,mul
from .contests import ss8,ss16,pop
from .restarts import _end,idiv_by
from .setup import guest,player_of,squad_of,rb,rw,w8,w16
from .silent import save_ptr,_ds_far

PORTS=Registry('ageing','In-season80DA and its complete retirement/replacement/managed-pool closure (T124f)')
PORTS.variant('age-increment-dropped','7E6F: omit incrementing a nonzero player age')
PORTS.variant('retirement-threshold-plus-one','7F78: retire uncapped players one year too late')
PORTS.variant('replacement-draw-dropped','7EC7: omit the first replacement RNG6 draw')
PORTS.variant('pool-scorer-write-dropped','7FD4: omit scorer-count clear on the managed-pool caller8073')
M16=0xFFFF
GAME,PLAYERS,COUNTRIES,POOL=0xA923,0xA91B,0xA917,0xA927


def _local(mem,r,off):
    r.di=ss16(mem,r,r.bp+off);r.es=ss16(mem,r,r.bp+off+2)


@PORTS.port('1771:0000',ret='retf')
def draw_initial(mem,variant):
    r=Regs(mem);r.enter(2)
    r.al=mem.ds8(0x0C38);r.ah=0
    r=yield from guest(mem,r,'214B:06B1',r.ax,ret='1771:0011')
    r.di=r.ax;r.al=mem.ds8((r.di+0x0C38)&M16);r.local8(-1,r.al)
    r.al=ss8(mem,r,r.bp-1)
    return _end(r)


@PORTS.port('1771:3291',ret='ret 2')
def roll_peak_age(mem,variant):
    r=Regs(mem);r.enter(4)
    player_of(mem,r,ss16(mem,r,r.bp+4));save_ptr(r,-4)
    r.ax=3;r=yield from guest(mem,r,'214B:06B1',r.ax,ret='1771:32B4');r.push(r.ax)
    r.ax=3;r=yield from guest(mem,r,'214B:06B1',r.ax,ret='1771:32BE');r.dx=r.ax
    _local(mem,r,-4);r.al=int(rb(mem,r,7)==0);cbw(r);r.di=r.ax
    r.al=mem.ds8((r.di+0x0E80)&M16);r.ah=0;r.ax+=r.dx;r.dx=pop(mem,r);r.ax-=r.dx
    _local(mem,r,-4);w8(mem,r,2,r.al,'1771:32E1')
    return _end(r)


@PORTS.port('1771:32EB',ret='retf 2')
def compute_ability(mem,variant):
    r=Regs(mem);r.enter(8)
    player_of(mem,r,ss16(mem,r,r.bp+6));save_ptr(r,-8)
    _local(mem,r,-8);r.al=rb(mem,r,1)
    _local(mem,r,-8);below=r.al<rb(mem,r,2)
    outside=below
    if not below:
        _local(mem,r,-8);r.al=rb(mem,r,2);r.ah=0;r.ax+=3;r.dx=r.ax
        _local(mem,r,-8);r.al=rb(mem,r,1);r.ah=0
        outside=s16(r.ax)>s16(r.dx)
    if not outside:
        _local(mem,r,-8);r.al=rb(mem,r,3)
        _local(mem,r,-8);w8(mem,r,4,r.al,'1771:333A')
    else:
        _local(mem,r,-8);r.al=rb(mem,r,3);r.ah=0;r.local16(-4,r.ax)
        _local(mem,r,-8);r.al=rb(mem,r,2);r.ah=0;r.ax+=3;r.dx=r.ax
        _local(mem,r,-8);r.al=rb(mem,r,1);r.ah=0
        if s16(r.ax)>s16(r.dx):
            _local(mem,r,-8);r.al=rb(mem,r,2);r.ah=0;r.ax+=3;r.dx=r.ax
            _local(mem,r,-8);r.al=rb(mem,r,1);r.ah=0;r.ax-=r.dx;r.dx=r.ax
            r.ax=16;r.ax-=r.dx;r.local16(-2,r.ax)
        else:
            _local(mem,r,-8);r.al=rb(mem,r,1);r.ah=0;r.dx=r.ax
            _local(mem,r,-8);r.al=rb(mem,r,2);r.ah=0;r.ax-=r.dx
            idiv_by(r,2);r.dx=r.ax;r.ax=16;r.ax-=r.dx;r.local16(-2,r.ax)
        r.ax=ss16(mem,r,r.bp-4);mul(r,ss16(mem,r,r.bp-2))
        r.dx=0;r.cx=16;r.ax,r.dx=divmod(r.ax,r.cx)
        _local(mem,r,-8);w8(mem,r,4,r.al,'1771:33C3')
    return _end(r)


@PORTS.port('1771:7E4A',ret='ret 2')
def advance_player_age(mem,variant):
    r=Regs(mem);r.enter(4)
    player_of(mem,r,ss16(mem,r,r.bp+4));save_ptr(r,-4)
    if ss16(mem,r,r.bp+4)!=0:
        _local(mem,r,-4)
        if variant!='age-increment-dropped':w8(mem,r,1,rb(mem,r,1)+1,'1771:7E6F')
        r=yield from guest(mem,r,'1771:32EB',ss16(mem,r,r.bp+4),ret='1771:7E7A')
    return _end(r)


@PORTS.port('1771:7F40',ret='retf 2')
def retirement_test(mem,variant):
    r=Regs(mem);r.enter(6)
    player_of(mem,r,ss16(mem,r,r.bp+6));save_ptr(r,-5)
    _local(mem,r,-5);r.al=int(rb(mem,r,7)==0);cbw(r);r.di=r.ax
    r.al=mem.ds8((r.di+0x110E)&M16)
    _local(mem,r,-5)
    limit=(r.al+int(variant=='retirement-threshold-plus-one'))&0xFF
    first=limit<rb(mem,r,1)
    if first:
        _local(mem,r,-5);first=rw(mem,r,8)==0
    if first:r.al=1
    else:
        _local(mem,r,-5);r.al=rb(mem,r,2);r.ah=0;r.ax+=5;r.dx=r.ax
        _local(mem,r,-5);r.al=rb(mem,r,1);r.ah=0
        r.al=int(s16(r.ax)>s16(r.dx))
    r.local8(-1,r.al);r.al=ss8(mem,r,r.bp-1)
    return _end(r)


@PORTS.port('1771:96D3',ret='retf 8')
def make_player(mem,variant):
    r=Regs(mem);r.enter(4)
    player_of(mem,r,ss16(mem,r,r.bp+0xC));save_ptr(r,-4)
    r.al=ss8(mem,r,r.bp+0xA);_local(mem,r,-4);w8(mem,r,0,r.al,'1771:96F3')
    r.al=ss8(mem,r,r.bp+8);_local(mem,r,-4);w8(mem,r,7,r.al,'1771:96FC')
    _local(mem,r,-4);r.al=rb(mem,r,7);_local(mem,r,-4);w8(mem,r,6,r.al,'1771:970A')
    r.ax=16;r=yield from guest(mem,r,'214B:06B1',r.ax,ret='1771:9717')
    _local(mem,r,-4);w8(mem,r,5,r.al,'1771:971A')
    r.ax=7;r=yield from guest(mem,r,'214B:06B1',r.ax,ret='1771:9727');r.push(r.ax)
    r.ax=7;r=yield from guest(mem,r,'214B:06B1',r.ax,ret='1771:9731');r.dx=r.ax
    _local(mem,r,-4);r.al=int(rb(mem,r,7)==0);cbw(r);r.di=r.ax
    r.al=mem.ds8((r.di+0x118A)&M16);r.ah=0;r.ax-=r.dx;r.dx=pop(mem,r);r.ax+=r.dx
    _local(mem,r,-4);w8(mem,r,1,r.al,'1771:9754')
    r=yield from guest(mem,r,'1771:3291',ss16(mem,r,r.bp+0xC),ret='1771:975E',far=False)
    if ss8(mem,r,r.bp+6):
        # 9767 pushCS /9768 call110E7: 16-bit IP wraps to10E7, still FAR ABI.
        r=yield from guest(mem,r,'1771:10E7',ss16(mem,r,r.bp+0xA),ret='1771:976B')
        r.ax+=0x7F;_local(mem,r,-4);w8(mem,r,3,r.al,'1771:9771')
    else:
        r.ax=10;r=yield from guest(mem,r,'214B:06B1',r.ax,ret='1771:9780');r.push(r.ax)
        r=yield from guest(mem,r,'1771:10E7',ss16(mem,r,r.bp+0xA),ret='1771:9788')
        r.ax+=0x7F;r.ax-=10;r.dx=pop(mem,r);r.ax-=r.dx
        _local(mem,r,-4);w8(mem,r,3,r.al,'1771:9794')
    r=yield from guest(mem,r,'1771:32EB',ss16(mem,r,r.bp+0xC),ret='1771:979F')
    r.ax=32;r=yield from guest(mem,r,'214B:06B1',r.ax,ret='1771:97A8')
    _local(mem,r,-4);w8(mem,r,0xC,r.al,'1771:97AB')
    r=yield from guest(mem,r,'1771:3431',ss16(mem,r,r.bp+0xC),ret='1771:97B6')
    r=yield from guest(mem,r,'1771:3558',ss16(mem,r,r.bp+0xC),ret='1771:97BD')
    _local(mem,r,-4);w16(mem,r,0x12,0x7FFF,'1771:97C0')
    return _end(r)


@PORTS.port('1771:7E80',ret='ret 2')
def recreate_retired_player(mem,variant):
    r=Regs(mem);r.enter(6)
    player_of(mem,r,ss16(mem,r,r.bp+4));save_ptr(r,-6)
    _local(mem,r,-6);r.al=rb(mem,r,6);r.ah=0;r.local16(-2,r.ax)
    player=ss16(mem,r,r.bp+4)
    _local(mem,r,-6);r.al=rb(mem,r,0);r.ah=0;country=r.ax
    _local(mem,r,-6);r.al=rb(mem,r,7);r.ah=0;position=r.ax;r.al=1
    r=yield from guest(mem,r,'1771:96D3',player,country,position,r.ax,ret='1771:7EC3')
    r.ax=6
    if variant=='replacement-draw-dropped':r.ax=1
    else:r=yield from guest(mem,r,'214B:06B1',r.ax,ret='1771:7ECC')
    r.push(r.ax)
    r.ax=6;r=yield from guest(mem,r,'214B:06B1',r.ax,ret='1771:7ED6');r.dx=r.ax
    _local(mem,r,-6);r.al=int(rb(mem,r,7)==0);cbw(r);r.di=r.ax
    r.al=mem.ds8((r.di+0x110C)&M16);r.ah=0;r.ax+=r.dx;r.dx=pop(mem,r);r.ax-=r.dx
    _local(mem,r,-6);w8(mem,r,1,r.al,'1771:7EF9')
    r=yield from guest(mem,r,'1771:32EB',ss16(mem,r,r.bp+4),ret='1771:7F04')
    _local(mem,r,-6);r.ax=0;w16(mem,r,8,r.ax,'1771:7F09')
    _local(mem,r,-6);r.ax=0;w16(mem,r,0xA,r.ax,'1771:7F12')
    _local(mem,r,-6);w8(mem,r,0x10,0,'1771:7F19')
    r=yield from guest(mem,r,'1771:0000',ret='1771:7F22')
    r.dx=(r.dx&0xFF00)|r.al;r.ax=ss16(mem,r,r.bp+4)
    _ds_far(mem,r,0x9B70);r.di+=r.ax;w8(mem,r,0,r.dx&255,'1771:7F2D')
    r.al=ss8(mem,r,r.bp-2);_local(mem,r,-6);w8(mem,r,6,r.al,'1771:7F36')
    return _end(r)


@PORTS.port('1771:7FB1',ret='ret 4')
def age_one_player(mem,variant):
    r=Regs(mem);r.enter(4)
    player_of(mem,r,ss16(mem,r,r.bp+6));save_ptr(r,-4)
    r=yield from guest(mem,r,'1771:7E4A',ss16(mem,r,r.bp+6),ret='1771:7FD1',far=False)
    _local(mem,r,-4)
    if not(variant=='pool-scorer-write-dropped' and ss16(mem,r,r.bp+2)==0x8073):
        w8(mem,r,0x11,0,'1771:7FD4')
    return _end(r)


@PORTS.port('1771:7FDF',ret='ret 2')
def age_country_squad(mem,variant):
    r=Regs(mem);r.enter(8)
    squad_of(mem,r,ss16(mem,r,r.bp+4));save_ptr(r,-6);r.local16(-2,1)
    while True:
        r.ax=ss16(mem,r,r.bp-2);r.ax<<=1;_local(mem,r,-6);r.di+=r.ax
        player=rw(mem,r,-2)
        r=yield from guest(mem,r,'1771:7FB1',player,r.bp,ret='1771:8015',far=False)
        if ss16(mem,r,r.bp-2)==20:break
        r.local16(-2,ss16(mem,r,r.bp-2)+1)
    r=yield from guest(mem,r,'1771:0B77',ss16(mem,r,r.bp+4),ret='1771:8022')
    if r.al:
        _local(mem,r,-6);r.al=rb(mem,r,0x2E);r.ah=0;r.ax-=0x80;r.di=r.ax;r.di<<=1
        r.ax=mem.ds16((r.di+0x6D18)&M16);r.ax+=0x4F;r.local16(-8,r.ax)
        _local(mem,r,-6);r.al=rb(mem,r,0x2E);r.ah=0;r.ax-=0x80;r.di=r.ax;r.di<<=1
        r.ax=mem.ds16((r.di+0x6D18)&M16)
        if r.ax<=ss16(mem,r,r.bp-8):
            r.local16(-2,r.ax)
            while True:
                r.ax=ss16(mem,r,r.bp-2);r.ax<<=1;_ds_far(mem,r,POOL);r.di+=r.ax
                player=rw(mem,r,0)
                r=yield from guest(mem,r,'1771:7FB1',player,r.bp,ret='1771:8073',far=False)
                r.ax=ss16(mem,r,r.bp-2)
                if r.ax==ss16(mem,r,r.bp-8):break
                r.local16(-2,ss16(mem,r,r.bp-2)+1)
    else:
        r.local16(-2,1)
        while True:
            r.ax=ss16(mem,r,r.bp-2);r.ax<<=1;_local(mem,r,-6);r.di+=r.ax
            r=yield from guest(mem,r,'1771:7F40',rw(mem,r,-2),ret='1771:8099')
            if r.al:
                r.ax=ss16(mem,r,r.bp-2);r.ax<<=1;_local(mem,r,-6);r.di+=r.ax
                r=yield from guest(mem,r,'1771:7E80',rw(mem,r,-2),ret='1771:80AE',far=False)
            if ss16(mem,r,r.bp-2)==20:break
            r.local16(-2,ss16(mem,r,r.bp-2)+1)
    return _end(r)


@PORTS.port('1771:80DA',ret='ret')
def in_season_ageing(mem,variant):
    # Guard before Regs.enter, hence before even a saved-BP/local stack write.
    stage=mem.u8(mem.addr(mem.ds16(GAME+2),mem.ds16(GAME)+0x3C))
    if stage not in (3,7):
        raise PortError(f'1771:80DA deferred year rollover/unsupported stage {stage}; supported in-season stages3/7')
    r=Regs(mem);r.enter(0xC)
    _ds_far(mem,r,GAME);save_ptr(r,-8);r.local16(-2,1)
    while True:
        r=yield from guest(mem,r,'1771:7FDF',ss16(mem,r,r.bp-2),ret='1771:80FA',far=False)
        if ss16(mem,r,r.bp-2)==128:break
        r.local16(-2,ss16(mem,r,r.bp-2)+1)
    _local(mem,r,-8);r.al=rb(mem,r,0x3C);r.di=0x80BA
    r=yield from guest(mem,r,'23E4:08DF',r.ax,mem.seg(0x1771),r.di,ret='1771:8113')
    # Original CS:80BA contains stages2/5 only; admitted stages3/7 take81E4.
    return _end(r)
