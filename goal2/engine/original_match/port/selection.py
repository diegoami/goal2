"""T75 SELECT TEAM and first-eleven validation, transcribed from the named view
and code/seg_0791_22.asm, seg_0791_23.asm and seg_1771_08.asm.
The key adapter supplies keys; these bodies retain the original frames and calls.
"""
from . import Registry
from .contests import ss16, ss8
from .geometry import cbw, mul
from .runtime import Regs
from .restarts import _end
from .setup import guest, farg, rb, rw, w8, w16, squad_of, player_of, ss_w16

PORTS=Registry('selection', 'SELECT TEAM, substitutions and first-eleven checks (T75)')
PORTS.variant('request-not-set','E6A9 omits the substitution request')
PORTS.variant('form-not-swapped','E20B omits the match-form swap')
PORTS.variant('keeper-check-inverted','EB89 rejects one keeper instead of two')
M16=0xFFFF


def parent(mem,r):
    r.di=ss16(mem,r,r.bp+4)
    return r.di


def pword(mem,r,k):
    return ss16(mem,r,parent(mem,r)+k)


def pbyte(mem,r,k):
    return ss8(mem,r,parent(mem,r)+k)


def putp(r,off,value,byte=False):
    if byte:r._put(off,bytes([value&255]))
    else:ss_w16(r,off,value)


def pool_word(mem,r,index):
    r.ax=index<<1;r.di,r.es=mem.ds16(0xA927),mem.ds16(0xA929);r.di=r.di+r.ax
    return rw(mem,r,0)


def slot(mem,r,index):
    r.ax=index<<1;farg(mem,r,-8);r.di=r.di+r.ax
    return rw(mem,r,-2)


@PORTS.port('0791:DE27',ret='ret 2')
def selected_index(mem,variant):
    r=Regs(mem);r.enter(2)
    if pword(mem,r,-5)==1:r.ax=mem.ds16(0xC1B)
    else:r=yield from guest(mem,r,'DDCB',ss16(mem,r,r.bp+4),ret='DE45',far=False)
    r.local16(-2,r.ax);r.ax=ss16(mem,r,r.bp-2)
    return _end(r)


@PORTS.port('0791:DE51',ret='ret 6')
def selected_pointer(mem,variant):
    r=Regs(mem);r.enter(4)
    if ss16(mem,r,r.bp+8)==1:
        r.ax=ss16(mem,r,r.bp+6)<<1;r.cx=r.ax
        squad_of(mem,r,pword(mem,r,6));r.di=r.di+r.cx;r.ax=r.di-2;r.dx=r.es
    else:
        r.ax=ss16(mem,r,r.bp+6)<<1;r.di,r.es=mem.ds16(0xA927),mem.ds16(0xA929)
        r.di=r.di+r.ax;r.ax=r.di;r.dx=r.es
    r.local16(-4,r.ax);r.local16(-2,r.dx)
    r.ax=ss16(mem,r,r.bp-4);r.es=ss16(mem,r,r.bp-2);r.dx=r.es
    return _end(r)


@PORTS.port('0791:E949',ret='ret 2')
def open_selection(mem,variant):
    r=Regs(mem);r.enter()
    r=yield from guest(mem,r,'1771:0B77',pword(mem,r,-5),ret='E958')
    if not r.al:
        country=pword(mem,r,-5);r.ax=1
        r=yield from guest(mem,r,'1771:50F1',country,r.ax,ret='E96C')
    else:
        squad_of(mem,r,pword(mem,r,-5));r.al=rb(mem,r,0x2E);r.ah=0;r.ax=r.ax-0x80
        r.di,r.es=mem.ds16(0xA923),mem.ds16(0xA925);w8(mem,r,1,r.al,'E98D')
        r=yield from guest(mem,r,'E44F',pword(mem,r,-5),ret='E99C')
    return _end(r)


def template(mem,r,off,ret):
    r.di=off;source=mem.DS,r.di;r.di=0xA96E
    return (yield from guest(mem,r,'214B:0329',*source,mem.DS,r.di,ret=ret))


@PORTS.port('0791:E2A0',ret='ret 2')
def substitution_instructions(mem,variant):
    r=Regs(mem);r.enter()
    r=yield from template(mem,r,0x4840,'E2B2')
    if mem.ds16(0xC1B)>11:r=yield from template(mem,r,0x4740,'E2C8')
    elif mem.ds16(0xC1B)<12:r=yield from template(mem,r,0x4720,'E2E0')
    return _end(r)


@PORTS.port('0791:E44F',ret='retf 2')
def select_team(mem,variant):
    r=Regs(mem);r.enter(0x12)
    r.di,r.es=mem.ds16(0xA923),mem.ds16(0xA925);r.local16(-17,r.di);r.local16(-15,r.es)
    squad_of(mem,r,ss16(mem,r,r.bp+6));r.al=rb(mem,r,0x2E);r.ah=0;r.ax=r.ax-0x80
    farg(mem,r,-17);w8(mem,r,1,r.al,'E479')
    if not mem.ds8(0xC1E):
        mem.wds8(0xC20,0,'0791:E484')
        r=yield from guest(mem,r,'1771:52CC',ss16(mem,r,r.bp+6),ret='E491')
    r.local8(-1,0);r.local16(-5,1)
    if mem.ds8(0xC1E):r.al=int(mem.ds16(0x9B36)==ss16(mem,r,r.bp+6));r.local8(-3,r.al)
    r.ax=0;r.local16(-11,0)
    while True:
        if ss16(mem,r,r.bp-5)==1:
            country=ss16(mem,r,r.bp+6);r.al=mem.ds8(0xC20);cbw(r);r.di=r.ax
            r.al=mem.ds8((r.di+0xABC)&M16);r.ah=0
            r=yield from guest(mem,r,'1771:4E22',country,r.ax,ret='E4D2')
        else:r=yield from guest(mem,r,'E2E6',r.bp,ret='E4D8',far=False)
        if mem.ds8(0xC20):r=yield from template(mem,r,0x1AF6,'E4EE')
        if not mem.ds8(0x66D):
            if mem.ds8(0xC20):r=yield from template(mem,r,0x2568,'E50E')
            elif not mem.ds8(0xC1F):
                r=yield from template(mem,r,0x1B42,'E527')
                if ss16(mem,r,r.bp-5)==1:r=yield from template(mem,r,0x58E6,'E53C')
            else:
                r.al=ss8(mem,r,r.bp-3);cbw(r);r.di=r.ax
                if not mem.ds8((r.di+0x9B3A)&M16):r=yield from template(mem,r,0x2538,'E55A')
                elif mem.ds8(0x9B41):r=yield from guest(mem,r,'E2A0',r.bp,ret='E567',far=False)
                elif not mem.ds8(0x9B40):r=yield from template(mem,r,0x4760,'E57F')
                else:
                    r=yield from template(mem,r,0x4812,'E590');r=yield from template(mem,r,0x4EB2,'E59F')
        if ss8(mem,r,r.bp-1):
            if not mem.ds8(0xC1F):r=yield from template(mem,r,0x2672,'E5BB')
            if ss16(mem,r,r.bp-7)==1 and ss16(mem,r,r.bp-5)==1 and mem.ds16(0xC1B)!=ss16(mem,r,r.bp-9):
                selected=ss16(mem,r,r.bp-9);r.al=int(selected>11);r.ah=0;r.dx=r.ax
                r.ax=selected+2+r.dx;r.dx=0xA0;mul(r,r.dx)
                r.di,r.es=mem.ds16(0xA96E),mem.ds16(0xA970);r.di=r.di+r.ax-0x20
                ptr=r.es,r.di;r.ax=0x8F;attr=r.ax;r.ax=12
                r=yield from guest(mem,r,'214B:00DB',*ptr,attr,r.ax,ret='E605')
        r.di,r.es=mem.ds16(0xA96E),mem.ds16(0xA970);source=r.es,r.di
        r.di,r.es=mem.ds16(0xA96A),mem.ds16(0xA96C);r.ax=4000
        r=yield from guest(mem,r,'23E4:025D',*source,r.es,r.di,r.ax,ret='E61A')
        r=yield from guest(mem,r,'214B:08DD',ret='E61F')
        r.local8(-2,0)
        if mem.ds8(0xA976)==0x1B and not ss8(mem,r,r.bp-1):
            if ss16(mem,r,r.bp-5)==1:r.local8(-2,1)
            else:mem.wds8(0xA976,0xAE,'0791:E63C')
        if ss8(mem,r,r.bp-1) and mem.ds8(0xA976)==0x1B:
            r.local8(-1,0);r.ax=0;r.local16(-11,0)
        else:
            r.al=mem.ds8(0xA976);r=yield from guest(mem,r,'23E4:19B2',r.ax,ret='E663');key=r.al
            if key==13:
                if not mem.ds8(0xC1F):r=yield from guest(mem,r,'DEA6',r.bp,ret='E672',far=False)
                elif not mem.ds8(0xC20):
                    if mem.ds8(0x9B41):
                        r.al=ss8(mem,r,r.bp-3);cbw(r);r.di=r.ax
                    if mem.ds8(0x9B41) and mem.ds8((r.di+0x9B3A)&M16)>0:
                        r=yield from guest(mem,r,'E022',r.bp,ret='E693',far=False)
                    else:
                        if not mem.ds8(0x9B40):
                            r.al=ss8(mem,r,r.bp-3);cbw(r);r.di=r.ax
                            if mem.ds8((r.di+0x9B3A)&M16)>0:
                                if variant!='request-not-set':mem.wds8(0x9B40,1,'0791:E6A9')
                            else:mem.wds8(0x9B40,0,'0791:E6B0')
                        else:mem.wds8(0x9B40,0,'0791:E6B0')
            elif key in (0xAE,0xAF):
                if not mem.ds8(0xC1F):r.local16(-5,2 if ss16(mem,r,r.bp-5)==1 else 1)
            elif key in (0xA0,ord('R'),ord('C'),ord('T')):
                if key==0xA0 or not mem.ds8(0xC20):
                    side=ss16(mem,r,r.bp-5);r.push(side)
                    r=yield from guest(mem,r,'DE27',r.bp,ret={0xA0:'E6E7',82:'E719',67:'E719',84:'E73F'}[key],far=False)
                    # The side word is held below DE27's sole parent argument.
                    side=ss16(mem,r,r.bp-5);r.sp=r.sp+2
                    r=yield from guest(mem,r,'DE51',side,r.ax,r.bp,ret={0xA0:'E6EC',82:'E71E',67:'E71E',84:'E744'}[key],far=False)
                    r.di=r.ax;r.es=r.dx;word=rw(mem,r,0)
                    if key==0xA0:
                        r.ax=8;a=r.ax;r.ax=2;r=yield from guest(mem,r,'1771:4859',word,a,r.ax,ret='E700')
                    elif key in (82,67):r=yield from guest(mem,r,'1771:4952',word,ret='E72A')
                    else:
                        r.al=int(side==1);r=yield from guest(mem,r,'1771:4B61',word,r.ax,ret='E75D')
            elif key==0xB6:
                if ss16(mem,r,r.bp-5)==1:
                    farg(mem,r,-17);r.al=rb(mem,r,1);r.ah=0;farg(mem,r,-17);r.di=r.di+r.ax
                    if not rb(mem,r,0x47) and not mem.ds8(0xC1F):r=yield from guest(mem,r,'DC7E',ret='E788',far=False)
            elif ss16(mem,r,r.bp-5)==1:
                r.di=0xC1B;r.ax=20;r=yield from guest(mem,r,'214B:1507',mem.DS,r.di,r.ax,ret='E79E')
            else:
                farg(mem,r,-17);r.al=rb(mem,r,1);r.ah=0;r.ax=r.ax<<1;farg(mem,r,-17);r.di=r.di+r.ax+0x5E;cursor=r.es,r.di
                farg(mem,r,-17);r.al=rb(mem,r,1);r.ah=0;r.ax=r.ax<<1;farg(mem,r,-17);r.di=r.di+r.ax+0x52;top=r.es,r.di
                r.ax=21;page=r.ax;r.ax=80;r=yield from guest(mem,r,'214B:15B1',*cursor,*top,page,r.ax,ret='E7D9')
        if ss8(mem,r,r.bp-2):break
    r=yield from guest(mem,r,'1771:5532',ret='E7E7')
    return _end(r)


@PORTS.port('0791:E022',ret='ret 2')
def swap_in_match(mem,variant):
    r=Regs(mem);r.enter(0x108)
    if not pbyte(mem,r,-1):
        side=pword(mem,r,-5);r.push(side)
        r=yield from guest(mem,r,'DE27',ss16(mem,r,r.bp+4),ret='E040',far=False)
        index=r.ax;r.sp=r.sp+2
        r=yield from guest(mem,r,'DE51',side,index,ss16(mem,r,r.bp+4),ret='E047',far=False)
        r.di=r.ax;r.es=r.dx;r.al=int(rw(mem,r,0)==0)
        flag=r.ax;r.di=0xDFDF
        r=yield from guest(mem,r,'214B:1765',flag,mem.seg(0x0791),r.di,ret='E062')
        if not r.al:
            r=yield from guest(mem,r,'DE27',ss16(mem,r,r.bp+4),ret='E06F',far=False)
            putp(r,parent(mem,r)-9,r.ax);r.ax=pword(mem,r,-5);putp(r,parent(mem,r)-7,r.ax)
            putp(r,parent(mem,r)-1,1,True)
        return _end(r)
    putp(r,parent(mem,r)-1,0,True)
    r.al=int(pword(mem,r,-9)<12);r.dx=(r.dx&0xFF00)|r.al
    r.al=int(mem.ds16(0xC1B)<12);r.al=int(r.al==(r.dx&255));flag=r.ax;r.di=0xDFF7
    r=yield from guest(mem,r,'214B:1765',flag,mem.seg(0x0791),r.di,ret='E0CB')
    if r.al:return _end(r)
    r.ax=mem.ds16(0xC1B);r.dx=0;current=r.ax;selected=pword(mem,r,-9);r.ax=selected;r.dx=0
    r=yield from guest(mem,r,'214B:0D56',0,current,0,selected,ret='E0E9');r.local16(-2,r.ax)
    r.ax=mem.ds16(0xC1B);r.dx=0;current=r.ax;selected=pword(mem,r,-9);r.ax=selected;r.dx=0
    r=yield from guest(mem,r,'214B:0D1C',0,current,0,selected,ret='E103');r.local16(-4,r.ax)
    squad_of(mem,r,pword(mem,r,6));r.local16(-8,r.di);r.local16(-6,r.es)
    word=slot(mem,r,ss16(mem,r,r.bp-2))
    r=yield from guest(mem,r,'1771:3216',word,ret='E131')
    flag=r.ax;r.push(flag);r.di=r.bp-0x108;expression=r.di;r.push(r.ss);r.push(r.di)
    word=slot(mem,r,ss16(mem,r,r.bp-2));r.ax=word;r.dx=11;mul(r,r.dx)
    r.di,r.es=mem.ds16(0x9B6C),mem.ds16(0x9B6E);r.di=r.di+r.ax
    r=yield from guest(mem,r,'23E4:062A',r.es,r.di,ret='E158')
    r.di=0xE00C;r=yield from guest(mem,r,'23E4:06B7',mem.seg(0x0791),r.di,ret='E162')
    r.sp=r.sp+6
    r=yield from guest(mem,r,'214B:1765',flag,r.ss,expression,ret='E167')
    if r.al:return _end(r)
    r.ax=6;element=r.ax;r.push(element)
    word=slot(mem,r,ss16(mem,r,r.bp-4));player_of(mem,r,word);r.al=rb(mem,r,16);r.ah=0;r.sp=r.sp+2
    r=yield from guest(mem,r,'214B:0C57',element,r.ax,ret='E194')
    flag=r.ax;r.di=0xE019;r=yield from guest(mem,r,'214B:1765',flag,mem.seg(0x0791),r.di,ret='E19F')
    if r.al:return _end(r)
    r.ax=ss16(mem,r,r.bp-2)<<1;farg(mem,r,-8);r.di=r.di+r.ax-2;bench=r.es,r.di
    r.ax=ss16(mem,r,r.bp-4)<<1;farg(mem,r,-8);r.di=r.di+r.ax-2;pitch=r.es,r.di;r.ax=2
    r=yield from guest(mem,r,'214B:007B',*bench,*pitch,r.ax,ret='E1CF')
    r.ax=ss16(mem,r,r.bp-2);r.cx=r.ax;r.al=pbyte(mem,r,-3);cbw(r);r.dx=20;mul(r,r.dx)
    r.di=r.ax+r.cx+0x9B07;bench=mem.DS,r.di
    r.ax=ss16(mem,r,r.bp-4);r.cx=r.ax;r.al=pbyte(mem,r,-3);cbw(r);r.dx=20;mul(r,r.dx)
    r.di=r.ax+r.cx+0x9B07;pitch=mem.DS,r.di;r.ax=1
    if variant!='form-not-swapped':r=yield from guest(mem,r,'214B:007B',*bench,*pitch,r.ax,ret='E210')
    r.ax=ss16(mem,r,r.bp-4)<<1;r.cx=r.ax;r.al=pbyte(mem,r,-3);cbw(r);r.dx=40;mul(r,r.dx)
    r.di=r.ax+r.cx;r.ax=0;mem.wds16((r.di+0x9A3E)&M16,0,'0791:E22A')
    r.ax=ss16(mem,r,r.bp-2)<<1;r.cx=r.ax;r.al=pbyte(mem,r,-3);cbw(r);r.dx=40;mul(r,r.dx)
    r.di=r.ax+r.cx+0x9A3E;bench=mem.DS,r.di
    r.ax=ss16(mem,r,r.bp-4)<<1;r.cx=r.ax;r.al=pbyte(mem,r,-3);cbw(r);r.dx=40;mul(r,r.dx)
    r.di=r.ax+r.cx+0x9A3E;pitch=mem.DS,r.di;r.ax=2
    r=yield from guest(mem,r,'214B:007B',*bench,*pitch,r.ax,ret='E273')
    r.al=pbyte(mem,r,-3);side=r.ax;r.al=pbyte(mem,r,-3);cbw(r);r.di=r.ax
    r.al=mem.ds8((r.di+0x668)&M16);r.ah=0;r.ax=r.ax+ss16(mem,r,r.bp-4)
    r=yield from guest(mem,r,'C5DC',side,r.ax,ss16(mem,r,r.bp-2),ret='E295',far=False)
    mem.wds8(0x9B40,0,'0791:E295')
    return _end(r)


def country_name(mem,r):
    r.ax=pword(mem,r,-5);r.cx=(r.cx&0xFF00)|4;r.ax=r.ax<<4
    r.di,r.es=mem.ds16(0x9B68),mem.ds16(0x9B6A);r.di=r.di+r.ax
    return r.es,r.di


def warning(mem,r,flag,local,parts,store_ret,concat_rets,message_ret):
    # Pascal string operations retain their result expression pointer below calls.
    r.push(flag);r.di=r.bp+local;expression=r.di;r.push(r.ss);r.push(r.di)
    source=country_name(mem,r)
    r=yield from guest(mem,r,'23E4:062A',*source,ret=store_ret)
    for (seg,off),ret in zip(parts,concat_rets):
        r.di=off;r=yield from guest(mem,r,'23E4:06B7',mem.seg(seg) if seg!=0x2581 else mem.DS,r.di,ret=ret)
    r.sp=r.sp+6
    return (yield from guest(mem,r,'214B:1765',flag,r.ss,expression,ret=message_ret))


@PORTS.port('0791:EA09',ret='ret 2')
def first_team_valid(mem,variant):
    r=Regs(mem);r.enter(0x418)
    r.ax=pword(mem,r,-5);r.local16(-21,r.ax);r.local8(-19,0)
    for side in range(2):
        if side:r.local8(-19,side)
        r.al=side;cbw(r);r.di=r.ax<<1
        r=yield from guest(mem,r,'1771:0B77',mem.ds16((r.di+0x9B34)&M16),ret='EA34')
        r.al=int(not r.al);r.dx=(r.dx&0xFF00)|r.al;r.al=ss8(mem,r,r.bp-19);cbw(r);r.di=r.ax;r.local8(r.di-23,r.dx&255)
    r.local8(-19,0)
    for side in range(2):
        if side:r.local8(-19,side)
        r.al=side;cbw(r);r.di=r.ax<<1
        r=yield from guest(mem,r,'1771:0B77',mem.ds16((r.di+0x9B34)&M16),ret='EA69')
        if not r.al:continue
        r.al=ss8(mem,r,r.bp-19);cbw(r);r.di=r.ax<<1;r.ax=mem.ds16((r.di+0x9B34)&M16)
        putp(r,parent(mem,r)-5,r.ax)
        r.di=r.bp-16;ptr=r.ss,r.di;r.ax=15;size=r.ax;r.ax=0
        r=yield from guest(mem,r,'214B:0018',*ptr,size,r.ax,ret='EA94')
        r.al=ss8(mem,r,r.bp-19);cbw(r);r.di=r.ax;r.local8(r.di-23,1);r.local16(-18,1)
        for index in range(1,12):
            if index>1:r.local16(-18,index)
            squad_of(mem,r,pword(mem,r,-5));r.local16(-27,r.di);r.local16(-25,r.es)
            r.ax=index<<1;farg(mem,r,-27);r.di=r.di+r.ax;word=rw(mem,r,-2)
            if not word:r.local8(-2,ss8(mem,r,r.bp-2)+1)
            else:
                r.ax=index<<1;farg(mem,r,-27);r.di=r.di+r.ax
                r=yield from guest(mem,r,'1771:3216',rw(mem,r,-2),ret='EAE9')
                if not r.al:
                    r.ax=index<<1;farg(mem,r,-27);r.di=r.di+r.ax;player_of(mem,r,rw(mem,r,-2))
                    r.al=rb(mem,r,6);r.ah=0;r.di=r.ax;r.local8(r.di-16,ss8(mem,r,r.bp+r.di-16)+1)
            if not mem.ds8(0xC1F):
                r.ax=index<<1;farg(mem,r,-27);r.di=r.di+r.ax
                r=yield from guest(mem,r,'1771:3216',rw(mem,r,-2),ret='EB2B')
                if r.al:
                    r.al=ss8(mem,r,r.bp-19);cbw(r);r.di=r.ax;r.local8(r.di-23,0)
        r.al=ss8(mem,r,r.bp-19);cbw(r);r.di=r.ax;r.al=int(not ss8(mem,r,r.bp+r.di-23))
        r=yield from warning(mem,r,r.ax,-0x117,[(0x0791,0xE9A2)],'EB73',['EB7D'],'EB82')
        if not r.al:
            r.al=int(ss8(mem,r,r.bp-16)>1) if variant!='keeper-check-inverted' else int(ss8(mem,r,r.bp-16)==1)
            r=yield from warning(mem,r,r.ax,-0x217,[(0x0791,0xE9CE),(0x2581,0x69B6),(0x0791,0xE9DD)],'EBB4',['EBBE','EBC8','EBD2'],'EBD7')
            if not r.al:
                r.al=int(ss8(mem,r,r.bp-16)==0)
                r=yield from warning(mem,r,r.ax,-0x317,[(0x0791,0xE9DF),(0x2581,0x69B6)],'EC09',['EC13','EC1D'],'EC22')
                if not r.al:
                    r.al=int(ss8(mem,r,r.bp-2)!=0)
                    r=yield from warning(mem,r,r.ax,-0x417,[(0x0791,0xE9E8)],'EC51',['EC5B'],'EC60')
            r.al=int(not r.al);r.dx=(r.dx&0xFF00)|r.al;r.al=ss8(mem,r,r.bp-19);cbw(r);r.di=r.ax;r.local8(r.di-23,r.dx&255)
        r.local16(-18,1)
        while ss8(mem,r,r.bp+side-23) and ss16(mem,r,r.bp-18)<=13:
            r.di=ss16(mem,r,r.bp-18);r.al=int(ss8(mem,r,r.bp+r.di-16)>3)
            position=ss16(mem,r,r.bp-18)
            r=yield from warning(mem,r,r.ax,-0x117,[(0x0791,0xE9CE),(0x2581,0x69B6+19*position),(0x0791,0xE9DD)],'ECBD',['ECC7','ECDC','ECE6'],'ECEB')
            r.al=int(not r.al);r.dx=(r.dx&0xFF00)|r.al;r.al=ss8(mem,r,r.bp-19);cbw(r);r.di=r.ax;r.local8(r.di-23,r.dx&255)
            r.local16(-18,ss16(mem,r,r.bp-18)+1)
    r.al=int(bool(ss8(mem,r,r.bp-23)) and bool(ss8(mem,r,r.bp-22)));r.local8(-1,r.al)
    r.ax=ss16(mem,r,r.bp-21);putp(r,parent(mem,r)-5,r.ax);r.al=ss8(mem,r,r.bp-1)
    return _end(r)


@PORTS.port('1771:5532',ret='retf')
def sort_pool(mem,variant):
    r=Regs(mem);r.enter(0x58)
    r.di,r.es=mem.ds16(0xA923),mem.ds16(0xA925);r.al=rb(mem,r,1);r.ah=0;r.di=r.ax<<1
    r.ax=mem.ds16((r.di+0x6D18)&M16);base=r.ax;r.local16(-84,base);r.local16(-82,1)
    for index in range(1,81):
        if index>1:r.local16(-82,index)
        word=pool_word(mem,r,(index+base-1)&M16);player_of(mem,r,word)
        r.local16(-88,r.di);r.local16(-86,r.es);farg(mem,r,-88);r.al=rb(mem,r,6)
        r.di=ss16(mem,r,r.bp-82);r.local8(r.di-81,r.al)
        word=pool_word(mem,r,(index+base-1)&M16)
        if not word:farg(mem,r,-88);w8(mem,r,6,14,'1771:559F')
    r.ax=base+79
    r=yield from guest(mem,r,'1771:53E8',base,r.ax,r.bp,ret='1771:55B8',far=False)
    r.local16(-82,1)
    for index in range(1,81):
        if index>1:r.local16(-82,index)
        word=pool_word(mem,r,(index+base-1)&M16);player_of(mem,r,word)
        r.local16(-88,r.di);r.local16(-86,r.es);r.di=ss16(mem,r,r.bp-82);r.al=ss8(mem,r,r.bp+r.di-81)
        farg(mem,r,-88);w8(mem,r,6,r.al,'1771:55EE')
    return _end(r)


def pool_position(mem,r,index):
    word=pool_word(mem,r,index);player_of(mem,r,word);r.al=rb(mem,r,6);r.ah=0
    return r.ax


@PORTS.port('1771:53E8',ret='ret 6')
def pool_quicksort(mem,variant):
    r=Regs(mem);r.enter(8)
    r.ax=ss16(mem,r,r.bp+8);r.local16(-2,r.ax)
    r.ax=ss16(mem,r,r.bp+6);r.local16(-4,r.ax)
    r.ax=(ss16(mem,r,r.bp+8)+ss16(mem,r,r.bp+6))&M16;r.dx=0;r.cx=2
    quotient,rem=divmod(r.ax,r.cx);r.ax=quotient;r.dx=rem
    pool_position(mem,r,r.ax);r.local16(-8,r.ax)
    while True:
        while pool_position(mem,r,ss16(mem,r,r.bp-2))<ss16(mem,r,r.bp-8):r.local16(-2,ss16(mem,r,r.bp-2)+1)
        while pool_position(mem,r,ss16(mem,r,r.bp-4))>ss16(mem,r,r.bp-8):r.local16(-4,ss16(mem,r,r.bp-4)-1)
        r.ax=ss16(mem,r,r.bp-2)
        if r.ax<=ss16(mem,r,r.bp-4):
            r.ax=pool_word(mem,r,ss16(mem,r,r.bp-2));r.local16(-6,r.ax)
            r.dx=pool_word(mem,r,ss16(mem,r,r.bp-4));pool_word(mem,r,ss16(mem,r,r.bp-2));w16(mem,r,0,r.dx,'1771:54AA')
            r.dx=ss16(mem,r,r.bp-6);pool_word(mem,r,ss16(mem,r,r.bp-4));w16(mem,r,0,r.dx,'1771:54BB')
            r.ax=ss16(mem,r,r.bp-2)-pword(mem,r,-84)+1;r.di=parent(mem,r)+r.ax-81;left=r.ss,r.di
            r.ax=ss16(mem,r,r.bp-4)-pword(mem,r,-84)+1;r.di=parent(mem,r)+r.ax-81;right=r.ss,r.di;r.ax=1
            r=yield from guest(mem,r,'214B:007B',*left,*right,r.ax,ret='1771:54F3')
            r.local16(-2,ss16(mem,r,r.bp-2)+1);r.local16(-4,ss16(mem,r,r.bp-4)-1)
        r.ax=ss16(mem,r,r.bp-2)
        if r.ax>ss16(mem,r,r.bp-4):break
    r.ax=ss16(mem,r,r.bp+8)
    if r.ax<ss16(mem,r,r.bp-4):
        r=yield from guest(mem,r,'1771:53E8',ss16(mem,r,r.bp+8),ss16(mem,r,r.bp-4),ss16(mem,r,r.bp+4),ret='1771:5518',far=False)
    r.ax=ss16(mem,r,r.bp-2)
    if r.ax<ss16(mem,r,r.bp+6):
        r=yield from guest(mem,r,'1771:53E8',ss16(mem,r,r.bp-2),ss16(mem,r,r.bp+6),ss16(mem,r,r.bp+4),ret='1771:552C',far=False)
    return _end(r)
