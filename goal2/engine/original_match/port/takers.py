"""T76 taker prompts, timed questions, extra time and shoot-out.

Named views read first; raw 0791 parts 02, 16 and 20 decide each frame,
argument word and return address. Calls remain guest calls, including keys.
"""
from . import Registry
from .contests import ss8, ss16, pop
from .geometry import cbw, mul
from .runtime import Regs
from .restarts import _end
from .setup import guest as _guest, farg, rb, rw, w8, squad_of, ss_w16

PORTS = Registry('takers', 'captain, set-piece takers, questions, extra time and shoot-out (T76)')
PORTS.variant('enter-keeps-current', 'CFD4 ignores the accepted highlighted player')
PORTS.variant('extra-time-short', '9B0F starts extra time with 30 rather than 31 clock units')
PORTS.variant('order-no-pushback', '9E5B drops the Down key pushed back after a selected taker')
M16 = 0xFFFF

# Earlier argument pushes at the listed call sites. Saved values and Pascal
# expression pointers which the callee leaves in place are deliberately absent.
EARLIER_ARGS = {'CD59':2,'CF85':2,'CE28':2,'CE50':2,'CE7D':2,'CEA2':5,
                'CEBD':4,'CFE9':2,'9F6D':1,'9FA2':1,'9FEE':4,'A024':1,
                'A068':1,'A08A':4,'A14D':3,'9C30':2,'9CC7':2,'9CDF':2,
                '9D51':2,'9D67':2,'9DE6':4}


def guest(mem,r,target,*args,ret,far=True):
    n=EARLIER_ARGS.get(ret,0)
    earlier=[ss16(mem,r,r.sp+2*i) for i in reversed(range(n))]
    r.sp=r.sp+2*n
    return (yield from _guest(mem,r,target,*earlier,*args,ret=ret,far=far))


def byte_arg(mem, r, k):
    return ss8(mem, r, r.bp+k)


def word(mem, r, k):
    return ss16(mem, r, r.bp+k)


def site(mem, r, at):
    r.store(stack=True)
    mem.site('0791:'+at)
    return Regs(mem, resumed=True)


def copy_screen(mem, r, source, dest, ret):
    r.di,r.es=mem.ds16(source),mem.ds16(source+2);src=r.es,r.di
    r.di,r.es=mem.ds16(dest),mem.ds16(dest+2);r.ax=4000
    return (yield from guest(mem,r,'23E4:025D',*src,r.es,r.di,r.ax,ret=ret))


def template(mem,r,off,ret,dest=0xA96E):
    r.di=off;src=mem.DS,r.di;r.di=dest
    return (yield from guest(mem,r,'214B:0329',*src,mem.DS,r.di,ret=ret))


@PORTS.port('0791:CC2E',ret='ret 2')
def wait_or_key(mem,variant):
    r=Regs(mem);r.enter(4)
    r=yield from guest(mem,r,'214B:1E8D',ret='CC39')
    r.ax=word(mem,r,4);r.local16(-4,r.ax);r.ax=1
    if r.ax<=word(mem,r,-4):
        r.local16(-2,r.ax)
        while True:
            r=yield from guest(mem,r,'214B:0723',ret='CC54')
            if r.al:break
            r.ax=10;r=yield from guest(mem,r,'214B:1E09',r.ax,ret='CC65')
            r.ax=word(mem,r,-2)
            if r.ax==word(mem,r,-4):break
            r.local16(-2,word(mem,r,-2)+1)
    return _end(r)


@PORTS.port('0791:0C0B',ret='ret')
def raise_speed(mem,variant):
    r=Regs(mem);r.enter(4)
    r.di,r.es=mem.ds16(0xA923),mem.ds16(0xA925);r.local16(-4,r.di);r.local16(-2,r.es)
    farg(mem,r,-4)
    if rb(mem,r,0x3F)<5:w8(mem,r,0x3F,rb(mem,r,0x3F)+1,'0C28')
    farg(mem,r,-4)
    if rb(mem,r,0x3F)<2:w8(mem,r,0x3F,2,'0C39')
    return _end(r)


@PORTS.port('0791:0B7C',ret='ret 4')
def ask_do_you_want(mem,variant):
    r=Regs(mem);r.enter(0x12A)
    source=farg(mem,r,4);r.di=r.bp-0x2A;r.ax=40
    r=yield from guest(mem,r,'23E4:0644',*source,r.ss,r.di,r.ax,ret='0B96')
    r.local8(-1,0);r=yield from guest(mem,r,'214B:0625',ret='0B9F')
    r.al=25;row=r.ax;r.push(r.ax);r.di=r.bp-0x12A;expression=r.di;r.push(r.ss);r.push(r.di);r.di=0xB67
    r=yield from guest(mem,r,'23E4:062A',mem.seg(0x791),r.di,ret='0BB2')
    r.di=r.bp-0x2A
    r=yield from guest(mem,r,'23E4:06B7',r.ss,r.di,ret='0BBC')
    r.di=0xB74;r=yield from guest(mem,r,'23E4:06B7',mem.seg(0x791),r.di,ret='0BC6')
    r.di=0xA96A
    r.sp=r.sp+6
    r=yield from guest(mem,r,'214B:0350',row,r.ss,expression,mem.DS,r.di,ret='0BD0')
    r.ax=600;r=yield from guest(mem,r,'CC2E',r.ax,ret='0BD7',far=False)
    r=yield from guest(mem,r,'214B:0643',ret='0BDC')
    r=yield from guest(mem,r,'214B:0723',ret='0BE1')
    if r.al:
        r=yield from guest(mem,r,'214B:08DD',ret='0BEC');r.al=mem.ds8(0xA976)
        r=yield from guest(mem,r,'23E4:19B2',r.ax,ret='0BF5')
        r.al=int(r.al==ord('Y'));r.local8(-1,r.al)
    r.al=byte_arg(mem,r,-1)
    return _end(r)


@PORTS.port('0791:9B0C',ret='ret')
def extra_time_first(mem,variant):
    r=Regs(mem);r.enter()
    mem.wds16(0x831B,30 if variant=='extra-time-short' else 31,'0791:9B0F')
    r=site(mem,r,'9B15');mem.wds16(0x831F,89,'0791:9B15')
    mem.wds8(0x8326,0,'0791:9B1B');mem.wds8(0x8319,15,'0791:9B20')
    r.ax=0;mem.wds16(0x831D,r.ax,'0791:9B27');r.al=62
    r=yield from guest(mem,r,'2B0F',r.ax,ret='9B30',far=False)
    mem.wds8(0x9B41,1,'0791:9B30')
    if mem.ds8(0x80FD):
        r.al=1;r=yield from guest(mem,r,'ED8A',r.ax,ret='9B42',far=False)
    r.al=mem.ds8(0x831A);cbw(r);r.di=r.ax;r.al=mem.ds8(0x668+r.di);r.ah=0;r.ax=r.ax+10
    mem.wds8(0x830B,r.al,'0791:9B51')
    r=yield from guest(mem,r,'983F',ret='9B57',far=False)
    return _end(r)


@PORTS.port('0791:9B5B',ret='ret')
def extra_time_second(mem,variant):
    r=Regs(mem);r.enter();mem.wds8(0x9B41,1,'0791:9B5E')
    if mem.ds8(0x80FD):
        r.al=1;r=yield from guest(mem,r,'ED8A',r.ax,ret='9B70',far=False)
    r.al=int(mem.ds8(0x831A)==0);cbw(r);r.di=r.ax;r.al=mem.ds8(0x668+r.di);r.ah=0;r.ax=r.ax+10
    mem.wds8(0x830B,r.al,'0791:9B89')
    r=yield from guest(mem,r,'983F',ret='9B8F',far=False)
    return _end(r)


def prompt_table(mem,r):
    r.al=byte_arg(mem,r,4);r.ah=0;r.ax=r.ax<<1;r.cx=r.ax
    r.al=byte_arg(mem,r,6);cbw(r);r.dx=10;mul(r,r.dx);r.di=r.ax+r.cx
    return (r.di+0x9976)&M16


def prompt_squad(mem,r,k):
    r.ax=k<<1;farg(mem,r,-13);r.di=r.di+r.ax
    return rw(mem,r,-2)


def computer_taker(mem,r,ret):
    r.al=byte_arg(mem,r,6);r.push(r.ax)
    r.al=byte_arg(mem,r,4);r.ah=0;r.di=r.ax;r.al=mem.ds8(r.di+0x764);r.ah=0;r.push(r.ax)
    r.al=byte_arg(mem,r,4);r.ah=0
    return (yield from guest(mem,r,'1FDD',r.ax,ret=ret,far=False))


@PORTS.port('0791:CC7B',ret='ret 4')
def choose_captain_or_taker(mem,variant):
    r=Regs(mem);r.enter(14)
    r.al=byte_arg(mem,r,6);cbw(r);r.di=r.ax<<1
    squad_of(mem,r,mem.ds16((r.di+0x9B34)&M16));r.local16(-13,r.di);r.local16(-11,r.es)
    r=yield from copy_screen(mem,r,0xA96A,0xA972,'CCB3')
    r.ax=0;r.local16(-5,0)
    if byte_arg(mem,r,4)==1:
        r=yield from guest(mem,r,'1771:3216',mem.ds16(prompt_table(mem,r)),ret='CCDD')
        bad=bool(r.al)
        if not bad:
            r.al=byte_arg(mem,r,6);side=r.ax;r.ax=1
            r=yield from guest(mem,r,'6B65',side,r.ax,ret='CCEC',far=False);bad=r.ax>11
        if bad:
            r.al=byte_arg(mem,r,6);r=yield from guest(mem,r,'1F3C',r.ax,ret='CCF8',far=False)
            r.cx=r.ax;r.al=byte_arg(mem,r,6);cbw(r);r.dx=10;mul(r,r.dx);r.di=r.ax
            mem.wds16((r.di+0x9978)&M16,r.cx,'0791:CD05')
    r=yield from guest(mem,r,'1771:3216',mem.ds16(prompt_table(mem,r)),ret='CD28')
    bad=bool(r.al)
    if not bad:
        r.al=byte_arg(mem,r,6);side=r.ax;r.al=byte_arg(mem,r,4);r.ah=0
        r=yield from guest(mem,r,'6B65',side,r.ax,ret='CD39',far=False);bad=r.ax>11
    if bad:r=yield from computer_taker(mem,r,'CD59')
    r.local16(-9,1)
    while True:
        r.bx=prompt_squad(mem,r,word(mem,r,-9));r.ax=mem.ds16(prompt_table(mem,r))
        if r.ax==r.bx:
            w=prompt_squad(mem,r,word(mem,r,-9));r=yield from guest(mem,r,'1771:3216',w,ret='CDA2')
            if not r.al:r.ax=word(mem,r,-9);r.local16(-5,r.ax)
        if word(mem,r,-9)==11:break
        r.local16(-9,word(mem,r,-9)+1)
    if word(mem,r,-5):r.ax=prompt_squad(mem,r,word(mem,r,-5));r.local16(-7,r.ax)
    else:r.ax=0;r.local16(-7,0);r.local16(-5,1)
    while True:
        mem.wds8(0xA976,0,'0791:CDD5');r.di=0x1ECC
        r=yield from guest(mem,r,'A699',mem.DS,r.di,ret='CDE2',far=False)
        r.ax=6;r=yield from guest(mem,r,'214B:05F0',r.ax,ret='CDEB')
        r=yield from template(mem,r,0x60EC,'CDFA')
        if byte_arg(mem,r,4)!=1:r=yield from template(mem,r,0x60D6,'CE0F')
        r.al=byte_arg(mem,r,6);cbw(r);r.di=r.ax<<1;r.push(mem.ds16((r.di+0x9B34)&M16))
        r.ax=23;r.push(r.ax);r.ax=65;r=yield from guest(mem,r,'1771:0F58',r.ax,ret='CE28')
        r.local16(-9,1)
        while True:
            w=prompt_squad(mem,r,word(mem,r,-9));r.push(w);r.ax=word(mem,r,-9)+7;r.push(r.ax);r.ax=65
            r=yield from guest(mem,r,'1771:2F37',r.ax,ret='CE50')
            if word(mem,r,-9)==11:break
            r.local16(-9,word(mem,r,-9)+1)
        w=prompt_squad(mem,r,word(mem,r,-5));r=yield from guest(mem,r,'1771:42BC',w,ret='CE69')
        r.ax=word(mem,r,-5)+7;r.push(r.ax);r.ax=65;r.push(r.ax);r.ax=13
        r=yield from guest(mem,r,'214B:13C5',r.ax,ret='CE7D')
        r.al=3;r.push(r.ax);r.al=byte_arg(mem,r,4);r.ah=0;r.dx=11;mul(r,r.dx);r.di=r.ax+0xA29
        r.push(mem.DS);r.push(r.di);r.al=25;r.push(r.ax);r.al=11;r.push(r.ax);r.di=0xA96E
        r=yield from guest(mem,r,'214B:02C8',mem.DS,r.di,ret='CEA2')
        if byte_arg(mem,r,4)==1:
            r.di=0xCC73;r.push(mem.seg(0x791));r.push(r.di);r.al=25;r.push(r.ax);r.al=19;r.push(r.ax);r.di=0xA96E
            r=yield from guest(mem,r,'214B:026D',mem.DS,r.di,ret='CEBD')
        r=yield from copy_screen(mem,r,0xA96E,0xA96A,'CED2')
        r.ax=1000;r=yield from guest(mem,r,'CC2E',r.ax,ret='CED9',far=False)
        r=yield from guest(mem,r,'214B:0723',ret='CEDE')
        if not r.al:r.local8(-3,1)
        else:
            r=yield from guest(mem,r,'214B:08DD',ret='CEED')
            r.al=int(mem.ds8(0xA976) in (13,27));r.local8(-3,r.al)
        if mem.ds8(0xA976)==32 and byte_arg(mem,r,4)!=1:
            r=yield from copy_screen(mem,r,0xA972,0xA96A,'CF26')
            r=yield from template(mem,r,0x14A6,'CF35',dest=0xA96A)
            r=yield from guest(mem,r,'214B:08DD',ret='CF3A')
        else:
            r.al=mem.ds8(0xA976);r=yield from guest(mem,r,'23E4:19B2',r.ax,ret='CF46')
            if r.al==ord('C'):
                if byte_arg(mem,r,4)==1:
                    r.al=byte_arg(mem,r,6);r=yield from guest(mem,r,'1F3C',r.ax,ret='CF57',far=False)
                    r.cx=r.ax;r.al=byte_arg(mem,r,6);cbw(r);r.dx=10;mul(r,r.dx);r.di=r.ax
                    mem.wds16((r.di+0x9978)&M16,r.cx,'0791:CF64')
                else:r=yield from computer_taker(mem,r,'CF85')
                r.ax=mem.ds16(prompt_table(mem,r));r.local16(-7,r.ax);r.local8(-3,1)
            elif mem.ds8(0xA976)==13:
                w=prompt_squad(mem,r,word(mem,r,-5));r=yield from guest(mem,r,'1771:3216',w,ret='CFC2')
                if not r.al:
                    r.ax=prompt_squad(mem,r,word(mem,r,-5))
                    if variant!='enter-keeps-current':r.local16(-7,r.ax)
                    r.local8(-3,1)
        r.di=r.bp-5;r.push(r.ss);r.push(r.di);r.ax=11
        r=yield from guest(mem,r,'214B:1507',r.ax,ret='CFE9')
        if byte_arg(mem,r,-3):break
    r=yield from copy_screen(mem,r,0xA972,0xA96A,'D007')
    r.ax=word(mem,r,-7);r.local16(-2,r.ax);r.ax=word(mem,r,-2)
    r=site(mem,r,'D010')
    return _end(r)


def parent(mem,r):
    r.di=word(mem,r,4)
    return r.di


def side(mem,r):
    r.al=ss8(mem,r,parent(mem,r)-31);cbw(r)
    return r.ax


def order_base(mem,r):
    side(mem,r);r.dx=12;mul(r,r.dx);r.di=word(mem,r,4)+r.ax
    return (r.di-26)&M16


def order_entry(mem,r,index):
    r.cx=index;off=order_base(mem,r);r.di=r.di+r.cx;r.al=ss8(mem,r,off+r.cx);r.ah=0
    return r.ax


def pitch_of(r,slot):
    r.ax=slot;r.dx=22;mul(r,r.dx);r.di=r.ax+0x80E8
    return r.di


@PORTS.port('0791:9ED3',ret='ret 2')
def computer_order(mem,variant):
    r=Regs(mem);r.enter(4);r.local16(-2,1)
    while True:
        side(mem,r);r.di=r.ax;r.al=mem.ds8(r.di+0x668);r.ah=0;r.ax=r.ax+word(mem,r,-2)
        value=r.al;r.ax=word(mem,r,-2);r.cx=r.ax
        off=order_base(mem,r);r.di=r.di+r.cx;r._put(off+r.cx,bytes([value]))
        if word(mem,r,-2)==11:break
        r.local16(-2,word(mem,r,-2)+1)
    r.local16(-4,1)
    while True:
        r.ax=word(mem,r,-4)+1
        if r.ax<=11:
            r.local16(-2,r.ax)
            while True:
                r.ax=12;r.push(r.ax);pitch_of(r,order_entry(mem,r,word(mem,r,-4)))
                r=yield from guest(mem,r,'278A',mem.DS,r.di,ret='9F6D')
                r.push(r.ax);r.ax=12;r.push(r.ax);pitch_of(r,order_entry(mem,r,word(mem,r,-2)))
                r=yield from guest(mem,r,'278A',mem.DS,r.di,ret='9FA2')
                r.dx=pop(mem,r)
                if r.ax>r.dx:
                    r.ax=word(mem,r,-2);r.cx=r.ax;off=order_base(mem,r);r.di=off+r.cx;r.push(r.ss);r.push(r.di)
                    r.ax=word(mem,r,-4);r.cx=r.ax;off=order_base(mem,r);r.di=off+r.cx;r.push(r.ss);r.push(r.di);r.ax=1
                    r=yield from guest(mem,r,'214B:007B',r.ax,ret='9FEE')
                if word(mem,r,-2)==11:break
                r.local16(-2,word(mem,r,-2)+1)
        if word(mem,r,-4)==10:break
        r.local16(-4,word(mem,r,-4)+1)
    return _end(r)


@PORTS.port('0791:A006',ret='ret 2')
def shootout_kick(mem,variant):
    r=Regs(mem);r.enter(2);r.push(mem.ds16(0x831D));side(mem,r);r.di=r.ax;r.al=mem.ds8(r.di+0x832E);r.ah=0
    r=yield from guest(mem,r,'054C',r.ax,ret='A024',far=False)
    r.al=ss8(mem,r,parent(mem,r)-31);r.ah=0;r.ax=-r.ax;mem.wds8(0x8319,r.al,'0791:A02F')
    t=side(mem,r);r.di=word(mem,r,4)+r.ax;r.al=ss8(mem,r,r.di-30);r.ah=0
    r.ax=order_entry(mem,r,r.ax);r.push(r.ax);r.al=10
    r=yield from guest(mem,r,'6BF1',r.ax,ret='A068',far=False)
    while True:
        t=side(mem,r);r.di=word(mem,r,4)+r.ax-30;r.push(r.ss);r.push(r.di)
        r.al=1;r.push(r.ax);r.al=11;r.push(r.ax);r.ax=1
        r=yield from guest(mem,r,'214B:1D6F',r.ax,ret='A08A')
        t=side(mem,r);r.di=word(mem,r,4)+r.ax;r.al=ss8(mem,r,r.di-30);r.ah=0
        pitch_of(r,order_entry(mem,r,r.ax));r=yield from guest(mem,r,'2956',mem.DS,r.di,ret='A0CA')
        if not r.al:break
    mem.wds8(0x8324,1,'0791:A0CE');mem.wds8(0x8325,0,'0791:A0D3')
    while True:
        r=yield from guest(mem,r,'9564',ret='A0DB',far=False)
        if not mem.ds8(0x8324):break
    r.al=0;r=yield from guest(mem,r,'2929',r.ax,ret='A0E8',far=False)
    while True:
        r=yield from guest(mem,r,'9564',ret='A0EB',far=False)
        if not mem.ds16(0x8300):break
    return _end(r)


@PORTS.port('0791:A10A',ret='ret')
def shootout(mem,variant):
    r=Regs(mem);r.enter(34)
    r.di,r.es=mem.ds16(0xA923),mem.ds16(0xA925);r.al=rb(mem,r,0x3F);r.ah=0;r.local16(-33,r.ax)
    r=yield from guest(mem,r,'0C0B',ret='A120',far=False)
    r.al=0;r=yield from guest(mem,r,'2929',r.ax,ret='A126',far=False)
    if mem.ds8(0x80FD):
        r.di=0xA0F8;r=yield from guest(mem,r,'214B:04F8',mem.seg(0x791),r.di,ret='A137')
    mem.wds8(0x9A3E,0,'0791:A137');r.di=r.bp-26;r.push(r.ss);r.push(r.di);r.ax=24;r.push(r.ax);r.ax=0
    r=yield from guest(mem,r,'214B:0018',r.ax,ret='A14D');r.local8(-31,0)
    while True:
        r.al=byte_arg(mem,r,-31);cbw(r);r.di=r.ax;r._put(r.bp+r.di-30,b'\x01')
        r.al=byte_arg(mem,r,-31);cbw(r);r.di=r.ax;r._put(r.bp+r.di-28,b'\x05')
        r.al=byte_arg(mem,r,-31);cbw(r);r.di=r.ax<<1
        r=yield from guest(mem,r,'1771:0B77',mem.ds16((r.di+0x9B34)&M16),ret='A17B')
        if r.al:r=yield from guest(mem,r,'9B93',r.bp,ret='A183',far=False)
        else:r=yield from guest(mem,r,'9ED3',r.bp,ret='A189',far=False)
        if byte_arg(mem,r,-31)==1:break
        r.local8(-31,byte_arg(mem,r,-31)+1)
    mem.wds16(0x831D,1,'0791:A18F');r.al=mem.ds8(0x831A);r.local8(-31,r.al)
    r=yield from guest(mem,r,'A841',ret='A19E',far=False)
    r=yield from copy_screen(mem,r,0x7C1E,0x7C16,'A1B3')
    r.al=61;r=yield from guest(mem,r,'2B0F',r.ax,ret='A1B9',far=False)
    while True:
        r.al=mem.ds8(0x9B3C);r.ah=0;r.cx=r.ax;r.al=byte_arg(mem,r,-27);r.ah=0;r.dx=r.ax
        r.al=mem.ds8(0x9B3D);r.ah=0;r.ax=r.ax+r.dx
        if r.ax<r.cx:break
        r.al=mem.ds8(0x9B3D);r.ah=0;r.cx=r.ax;r.al=byte_arg(mem,r,-28);r.ah=0;r.dx=r.ax
        r.al=mem.ds8(0x9B3C);r.ah=0;r.ax=r.ax+r.dx
        if r.ax<r.cx:break
        r=yield from guest(mem,r,'A006',r.bp,ret='A1EF',far=False)
        # The guest return to A1EF fires KICK_RETURN before resuming this frame.
        r.al=byte_arg(mem,r,-31);cbw(r);r.di=r.ax
        if ss8(mem,r,r.bp+r.di-28):
            r.al=byte_arg(mem,r,-31);cbw(r);r.di=r.ax;off=r.bp+r.di-28;r._put(off,bytes([(ss8(mem,r,off)-1)&255]))
        r.al=byte_arg(mem,r,-31)
        if r.al==mem.ds8(0x831A):
            cbw(r);r.di=r.ax
            if not ss8(mem,r,r.bp+r.di-28):
                r.al=int(byte_arg(mem,r,-31)==0);cbw(r);r.di=r.ax;r._put(r.bp+r.di-28,b'\x01')
        r.al=byte_arg(mem,r,-31)
        if r.al!=mem.ds8(0x831A):mem.wds16(0x831D,mem.ds16(0x831D)+1,'0791:A235')
        r.al=int(byte_arg(mem,r,-31)==0);r.local8(-31,r.al)
    r.al=byte_arg(mem,r,-33);r.di,r.es=mem.ds16(0xA923),mem.ds16(0xA925);w8(mem,r,0x3F,r.al,'A252')
    r.al=mem.ds8(0x9A3F);mem.wds8(0x9A3E,r.al,'0791:A259')
    return _end(r)


def order_squad(mem,r,index):
    r.ax=index<<1;farg(mem,r,-10);r.di=r.di+r.ax
    return rw(mem,r,-2)


def order_char(mem,r,index,ret):
    r.di=r.bp-0x10A;r.push(r.ss);r.push(r.di)
    side(mem,r);r.di=r.ax;r.al=mem.ds8(r.di+0x668);r.ah=0;r.ax=r.ax+index
    return (yield from guest(mem,r,'23E4:075A',r.ax,ret=ret))


def order_pos(mem,r,ret):
    r.sp=r.sp+4
    r.push(r.ss);r.push(r.bp-0x10A)
    r.di=order_base(mem,r)
    source=r.di;r.sp=r.sp+4
    return (yield from guest(mem,r,'23E4:06E3',r.ss,r.bp-0x10A,r.ss,source,ret=ret))


@PORTS.port('0791:9B93',ret='ret 2')
def managed_order(mem,variant):
    r=Regs(mem);r.enter(0x20A);side(mem,r);r.di=r.ax<<1
    squad_of(mem,r,mem.ds16((r.di+0x9B34)&M16));r.local16(-10,r.di);r.local16(-8,r.es)
    r=yield from copy_screen(mem,r,0x7C16,0x7C22,'9BD0')
    r.local16(-6,1);r.local16(-4,11);r.local16(-2,1)
    while True:
        w=order_squad(mem,r,word(mem,r,-2));r=yield from guest(mem,r,'1771:3216',w,ret='9BF7')
        if r.al:r.local16(-4,word(mem,r,-4)-1)
        if word(mem,r,-2)==11:break
        r.local16(-2,word(mem,r,-2)+1)
    r=yield from template(mem,r,0x4780,'9C13')
    side(mem,r);r.di=r.ax<<1;r.push(mem.ds16((r.di+0x9B34)&M16));r.ax=25;r.push(r.ax);r.ax=1
    r=yield from guest(mem,r,'1771:0F58',r.ax,ret='9C30')
    r=yield from template(mem,r,0x245E,'9C3F')
    while True:
        r=yield from template(mem,r,0x5FC4,'9C4E')
        w=order_squad(mem,r,word(mem,r,-6));r=yield from guest(mem,r,'1771:42BC',w,ret='9C61')
        r.local16(-2,1)
        while True:
            r=yield from order_char(mem,r,word(mem,r,-2),'9C8A');r=yield from order_pos(mem,r,'9CA7')
            if not r.ax:
                w=order_squad(mem,r,word(mem,r,-2));r.push(w);r.ax=word(mem,r,-2)+1;r.push(r.ax);r.ax=65
                r=yield from guest(mem,r,'1771:2F37',r.ax,ret='9CC7')
            if word(mem,r,-2)==11:break
            r.local16(-2,word(mem,r,-2)+1)
        r.ax=word(mem,r,-6)+1;r.push(r.ax);r.ax=65;r.push(r.ax);r.ax=13
        r=yield from guest(mem,r,'214B:13C5',r.ax,ret='9CDF')
        off=order_base(mem,r);r.al=ss8(mem,r,off);r.ah=0;r.local16(-12,r.ax);r.ax=1
        if r.ax<=word(mem,r,-12):
            r.local16(-2,r.ax)
            while True:
                slot=order_entry(mem,r,word(mem,r,-2));pitch_of(r,slot);r.local16(-16,r.di);r.local16(-14,mem.DS)
                farg(mem,r,-16);r.push(rw(mem,r,13));r.ax=word(mem,r,-2)+13;r.push(r.ax);r.ax=65
                r=yield from guest(mem,r,'1771:2F37',r.ax,ret='9D51')
                r.ax=word(mem,r,-2)
                if r.ax==word(mem,r,-12):break
                r.local16(-2,word(mem,r,-2)+1)
        r.di=r.bp-6;r.push(r.ss);r.push(r.di);r.ax=11
        r=yield from guest(mem,r,'214B:1560',r.ax,ret='9D67')
        while True:
            r=site(mem,r,'9D67')
            r=yield from order_char(mem,r,word(mem,r,-6),'9D86');r=yield from order_pos(mem,r,'9DA3')
            found=0<r.ax<0x8000
            if not found:
                w=order_squad(mem,r,word(mem,r,-6));r=yield from guest(mem,r,'1771:3216',w,ret='9DBA')
                if not r.al:break
            r.di=r.bp-6;r.push(r.ss);r.push(r.di);r.ax=1;r.push(r.ax);r.ax=11;r.push(r.ax)
            r.al=int(mem.ds8(0xA976)==0xB1);cbw(r);r.di=r.ax;r.al=mem.ds8(r.di+0x7920);cbw(r)
            r=yield from guest(mem,r,'214B:1C86',r.ax,ret='9DE6')
        if mem.ds8(0xA976)==13:
            r.di=r.bp-0x20A;r.push(r.ss);r.push(r.di);r.di=order_base(mem,r)
            r=yield from guest(mem,r,'23E4:062A',r.ss,r.di,ret='9E13')
            r=yield from order_char(mem,r,word(mem,r,-6),'9E32')
            r.sp=r.sp+4
            r=yield from guest(mem,r,'23E4:06B7',r.ss,r.bp-0x10A,ret='9E37')
            r.di=order_base(mem,r);r.push(r.ss);r.push(r.di);r.ax=11
            dest=r.di;r.sp=r.sp+8
            r=yield from guest(mem,r,'23E4:0644',r.ss,r.bp-0x20A,r.ss,dest,r.ax,ret='9E58')
            r.al=0xB1
            if variant!='order-no-pushback':r=yield from guest(mem,r,'214B:0993',r.ax,ret='9E60')
        elif mem.ds8(0xA976)==27:
            off=order_base(mem,r)
            if ss8(mem,r,off):
                off=order_base(mem,r);r._put(off,bytes([(ss8(mem,r,off)-1)&255]))
        off=order_base(mem,r);r.al=ss8(mem,r,off);r.ah=0
        if r.ax==word(mem,r,-4):break
    r=yield from copy_screen(mem,r,0x7C22,0x7C16,'9ECD')
    return _end(r)
