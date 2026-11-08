"""T125: original best twenty and its refusal/fixture predicates.

Static first: named/seg_0791_12.c DAF8–DC7E and named/seg_1771_04.c
55FC, then code/seg_0791_22.asm DAF8–DDCA and seg_1771_08.asm
55FC–56E3. Calls and local offsets below are the listing's, including
push-CS/near-call far frames and the Pascal strings' retained result pointer.
"""
from . import Registry
from .contests import ss16, ss8, pop
from .geometry import mul
from .restarts import _end
from .runtime import Regs, sub_flags
from .setup import guest, farg, rb, rw, squad_of, player_of

PORTS=Registry('assistant', 'Original recommended twenty and squad-change/fixture predicates (T125)')
PORTS.variant('ties-replace', 'DD82: replace an equal-strength incumbent too')
PORTS.variant('swap-omitted', 'DDA5: omit the squad/pool word swap')
PORTS.variant('next-write-omitted', '56A9/56CA: omit the next-fixture word write')


def dsfar(mem,r,ptr):
    r.di,r.es=mem.ds16(ptr),mem.ds16(ptr+2)
    return r.es,r.di


def manager_country(mem,r):
    dsfar(mem,r,0xA923);r.al=rb(mem,r,1);r.ah=0;r.ax+=0x80
    r.dx=3;mul(r,r.dx);dsfar(mem,r,0xA91F);r.di+=r.ax
    r.al=rb(mem,r,0);r.ah=0
    return r.ax


def fixture_from_list(mem,r,country,index):
    # DB5B–DB80 / 564B–5670 (the second lookup is repeated by the caller).
    r.ax=index<<1;r.cx=r.ax;r.ax=country;r.dx=0x48;mul(r,r.dx)
    dsfar(mem,r,0xA92F);r.di+=r.ax;r.di+=r.cx;r.ax=rw(mem,r,-2)
    return r.ax


def fixture_pointer(mem,r):
    r.cx=(r.cx&0xFF00)|3;r.ax<<=3;dsfar(mem,r,0xA92B);r.di+=r.ax


def test_al(r):
    r.arith(sub_flags(r.al,0,8))


@PORTS.port('1771:55FC',ret='retf')
def find_next_managed_fixture(mem,variant):
    r=Regs(mem);r.enter(6)
    dsfar(mem,r,0xA923);r.al=rb(mem,r,1);r.ah=0
    dsfar(mem,r,0xA923);r.di+=r.ax
    sacked=rb(mem,r,0x47);r.arith(sub_flags(sacked,0,8))
    if sacked:r.local8(-1,0)
    else:
        country=manager_country(mem,r);r.local16(-5,r.ax);r.local16(-3,0x24)
        while True:
            index=ss16(mem,r,r.bp-3);r.arith(sub_flags(index,0,16))
            if index==0:break
            fixture_from_list(mem,r,country,index);fixture_pointer(mem,r)
            r.arith(sub_flags(rb(mem,r,-8),0xFE,8))
            if rb(mem,r,-8)<0xFE:break
            fixture_from_list(mem,r,country,index);dsfar(mem,r,0xA923)
            r.arith(sub_flags(r.ax,rw(mem,r,0x26),16))
            if r.ax<rw(mem,r,0x26):break
            r.local16(-3,index-1)
        if index==0x24:r.ax=0
        else:
            r.ax=index;r.ax+=1;r.ax<<=1;r.cx=r.ax;r.ax=country;r.dx=0x48;mul(r,r.dx)
            dsfar(mem,r,0xA92F);r.di+=r.ax;r.di+=r.cx;r.ax=rw(mem,r,-2)
        if variant!='next-write-omitted':mem.wds16(0x9B43,r.ax,'1771:56A9' if index==0x24 else '1771:56CA')
        next_fixture=mem.ds16(0x9B43);r.arith(sub_flags(next_fixture,0,16))
        r.al=int(next_fixture>0);r.local8(-1,r.al)
    r.al=ss8(mem,r,r.bp-1)
    return _end(r)


@PORTS.port('0791:DAF8',ret='retf 2')
def next_fixture_is_tour(mem,variant):
    r=Regs(mem);r.enter(2)
    r=yield from guest(mem,r,'1771:55FC',ret='DB03');test_al(r)
    yes=False
    if r.al:
        country=ss16(mem,r,r.bp+6);r.ax=mem.ds16(0x9B43);fixture_pointer(mem,r);r.di-=8
        r=yield from guest(mem,r,'1771:5A38',country,r.es,r.di,ret='DB22');test_al(r)
        yes=bool(r.al)
    r.al=int(yes);r.local8(-1,r.al);r.al=ss8(mem,r,r.bp-1)
    return _end(r)


@PORTS.port('0791:DB38',ret='retf 2')
def on_tour(mem,variant):
    r=Regs(mem);r.enter(4);r.local8(-1,0)
    # DB45 push CS; DB46 near call: the callee still receives a far frame.
    r=yield from guest(mem,r,'DAF8',ss16(mem,r,r.bp+6),ret='DB49');test_al(r)
    if r.al:
        country=ss16(mem,r,r.bp+6);r.local16(-3,0x24)
        while True:
            index=ss16(mem,r,r.bp-3);r.arith(sub_flags(index,0,16))
            if index==0:break
            fixture_from_list(mem,r,country,index);fixture_pointer(mem,r)
            r.arith(sub_flags(rb(mem,r,-8),0xFE,8))
            if rb(mem,r,-8)<0xFE:break
            r.local16(-3,index-1)
        r.arith(sub_flags(index,0,16));yes=False
        if index:
            fixture_from_list(mem,r,country,index);fixture_pointer(mem,r);r.di-=8
            r=yield from guest(mem,r,'1771:5A38',country,r.es,r.di,ret='DBC5');test_al(r)
            yes=bool(r.al)
        r.al=int(yes);r.local8(-1,r.al)
    r.al=ss8(mem,r,r.bp-1)
    return _end(r)


def refusal_message(mem,r,flag,local,suffix,store_ret,concat_ret,message_ret):
    r.push(flag);r.di=r.bp+local;expression=r.di;r.push(r.ss);r.push(r.di)
    r.di=0xA9C
    r=yield from guest(mem,r,'23E4:062A',mem.DS,r.di,ret=store_ret)
    r.di=suffix
    r=yield from guest(mem,r,'23E4:06B7',mem.seg(0x0791),r.di,ret=concat_ret)
    r.sp+=6
    return (yield from guest(mem,r,'214B:1765',flag,r.ss,expression,ret=message_ret))


@PORTS.port('0791:DBFA',ret='ret 2')
def squad_change_allowed(mem,variant):
    r=Regs(mem);r.enter(0x206)
    dsfar(mem,r,0xA923);r.local16(-5,r.di);r.local16(-3,r.es)
    farg(mem,r,-5);r.al=rb(mem,r,1);r.ah=0;farg(mem,r,-5);r.di+=r.ax;r.al=rb(mem,r,0x13)
    r=yield from refusal_message(mem,r,r.ax,-0x105,0xDBDB,'DC2E','DC38','DC3D');test_al(r)
    allowed=False
    if not r.al:
        r=yield from guest(mem,r,'DB38',ss16(mem,r,r.bp+4),ret='DC48')
        r=yield from refusal_message(mem,r,r.ax,-0x205,0xDBEA,'DC59','DC63','DC68');test_al(r)
        allowed=not r.al
    r.al=int(allowed);r.local8(-1,r.al);r.al=ss8(mem,r,r.bp-1)
    return _end(r)


def pool_player(mem,r,index):
    r.ax=index<<1;dsfar(mem,r,0xA927);r.di+=r.ax
    return rw(mem,r,0)


def incumbent(mem,r,slot):
    r.ax=slot<<1;farg(mem,r,-0x10);r.di+=r.ax
    return rw(mem,r,-2)


@PORTS.port('0791:DC7E',ret='ret')
def recommend_squad(mem,variant):
    r=Regs(mem);r.enter(0x12)
    dsfar(mem,r,0xA923);r.local16(-0xC,r.di);r.local16(-0xA,r.es)
    country=manager_country(mem,r);r.local16(-8,r.ax)
    r=yield from guest(mem,r,'DBFA',country,ret='DCB3',far=False);test_al(r)
    if r.al:
        r.local16(-6,1)
        while True:
            squad_of(mem,r,ss16(mem,r,r.bp-8));r.local16(-0x10,r.di);r.local16(-0xE,r.es)
            r.local16(-4,1)
            while True:
                farg(mem,r,-0xC);r.al=rb(mem,r,1);r.ah=0;r.di=r.ax;r.di<<=1
                r.ax=mem.ds16(0x6D18+r.di);r.ax+=0x4F;r.local16(-0x12,r.ax)
                farg(mem,r,-0xC);r.al=rb(mem,r,1);r.ah=0;r.di=r.ax;r.di<<=1
                r.ax=mem.ds16(0x6D18+r.di)
                end=ss16(mem,r,r.bp-0x12)
                if r.ax<=end:
                    r.local16(-2,r.ax)
                    while True:
                        index=ss16(mem,r,r.bp-2);slot=ss16(mem,r,r.bp-4)
                        player_of(mem,r,pool_player(mem,r,index));r.cx=(r.cx&0xFF00)|rb(mem,r,6)
                        player_of(mem,r,incumbent(mem,r,slot));r.al=rb(mem,r,6)
                        if r.al==(r.cx&255):
                            word=pool_player(mem,r,index)
                            r=yield from guest(mem,r,'1771:377E',word,ret='DD6B');r.push(r.ax)
                            word=incumbent(mem,r,slot)
                            r=yield from guest(mem,r,'1771:377E',word,ret='DD7F');r.dx=pop(mem,r)
                            if r.ax<r.dx or (variant=='ties-replace' and r.ax==r.dx):
                                r.ax=slot<<1;farg(mem,r,-0x10);r.di+=r.ax;r.di-=2;dest=r.es,r.di
                                r.ax=index<<1;dsfar(mem,r,0xA927);r.di+=r.ax;src=r.es,r.di;r.ax=2
                                if variant!='swap-omitted':
                                    r=yield from guest(mem,r,'214B:007B',*dest,*src,r.ax,ret='DDAA')
                        r.ax=ss16(mem,r,r.bp-2)
                        if r.ax==ss16(mem,r,r.bp-0x12):break
                        r.local16(-2,r.ax+1)
                if ss16(mem,r,r.bp-4)==20:break
                r.local16(-4,ss16(mem,r,r.bp-4)+1)
            r.arith(sub_flags(ss16(mem,r,r.bp-6),2,16))
            if ss16(mem,r,r.bp-6)==2:break
            r.local16(-6,ss16(mem,r,r.bp-6)+1)
    return _end(r)
