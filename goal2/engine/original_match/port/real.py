"""T78b3a: 23E4's six-byte Real arithmetic, translated from the named/raw listings.

AL is the exponent; AH:BX:DX hold the fraction/sign. These are integer
translations of the library algorithms, not host floating-point operations or
an instruction interpreter. Local helpers retain flags and dead stack writes.
"""
from . import Registry
from .mem import PortError
from .runtime import Regs, ARITH, CF, PF, AF, ZF, SF, OF

PORTS=Registry('real','23E4 six-byte Real arithmetic and checked conversions')
MASK=0xFFFF

class RealRegs(Regs):
    __slots__=('flags',)
    def __init__(self,mem):
        super().__init__(mem)
        self.flags=mem.reg('eflags')
    def pop(self):
        self.flush()
        value=self._mem.u16(self._mem.ss_lin(self.sp))
        self.sp+=2
        return value
    def store(self,stack=False):
        self.arith(self.flags & ARITH)
        super().store(stack=stack)
    @property
    def carry(self):return int(bool(self.flags&CF))
    @property
    def zero(self):return bool(self.flags&ZF)
    @property
    def sign(self):return bool(self.flags&SF)
    def arithmetic(self,value,bits,carry=False,overflow=False,aux=False):
        value&=(1<<bits)-1
        f=(PF if (value&255).bit_count()%2==0 else 0)|(ZF if value==0 else 0)|(SF if value&(1<<(bits-1)) else 0)
        self.flags=(self.flags&~ARITH)|f|(CF if carry else 0)|(OF if overflow else 0)|(AF if aux else 0)
        return value
    def logic(self,value,bits=16):return self.arithmetic(value,bits)
    def add(self,a,b,bits=16,carry=0):
        mask=(1<<bits)-1;a&=mask;b&=mask;r=(a+b+carry)&mask
        return self.arithmetic(r,bits,a+b+carry>mask,(~(a^b)&(a^r)&(1<<(bits-1)))!=0,((a^b^r)&16)!=0)
    def sub(self,a,b,bits=16,carry=0):
        mask=(1<<bits)-1;a&=mask;b&=mask;r=(a-b-carry)&mask
        return self.arithmetic(r,bits,a<b+carry,((a^b)&(a^r)&(1<<(bits-1)))!=0,((a^b^r)&16)!=0)
    def inc(self,a,bits=16,delta=1):
        cf=self.carry
        value=self.add(a,1,bits) if delta==1 else self.sub(a,1,bits)
        self.flags=(self.flags&~CF)|cf
        return value
    def shl(self,a,bits=16):
        sign=1<<(bits-1);value=(a<<1)&((1<<bits)-1)
        return self.arithmetic(value,bits,bool(a&sign),bool(value&sign)!=bool(a&sign))
    def shr(self,a,bits=16):return self.arithmetic(a>>1,bits,bool(a&1),bool(a&(1<<(bits-1))))
    def rcl(self,a,bits=16):
        mask=(1<<bits)-1;value=((a<<1)|self.carry)&mask;cf=bool(a&(1<<(bits-1)))
        self.flags=(self.flags&~(CF|OF))|(CF if cf else 0)|(OF if bool(value&(1<<(bits-1)))!=cf else 0)
        return value
    def rcr(self,a,bits=16):
        value=(a>>1)|(self.carry<<(bits-1))
        self.flags=(self.flags&~(CF|OF))|(CF if a&1 else 0)|(OF if bool(value&(1<<(bits-1)))!=bool(value&(1<<(bits-2))) else 0)
        return value
    def mul(self,a,b,bits=16):
        product=(a&((1<<bits)-1))*(b&((1<<bits)-1))
        if bits==8:self.ax=product
        else:self.ax,self.dx=product,product>>16
        high=product>>bits
        self.flags=(self.flags&~(CF|OF))|((CF|OF) if high else 0)

# Byte aliases preserve the other half exactly as the source instructions do.
def _byte(word,shift):
    def get(r):return (getattr(r,word)>>shift)&255
    def put(r,value):setattr(r,word,(getattr(r,word)&~(255<<shift))|((value&255)<<shift))
    return property(get,put)
for _name,_word,_shift in (('cl','cx',0),('ch','cx',8),('dl','dx',0),('dh','dx',8)):
    setattr(RealRegs,_name,_byte(_word,_shift))


def zero(R):                           # 0B50–0B56
    R.ax=R.logic(0);R.bx=R.dx=R.ax


def from_long(R):                      # 0BF8–0C36
    R.bx=R.logic(R.ax|R.dx)
    if R.zero:return
    R.ch=R.dh
    R.logic(R.dx)
    if R.sign:
        R.ax=~R.ax;R.dx=~R.dx
        R.ax=R.add(R.ax,1);R.dx=R.add(R.dx,0,carry=R.carry)
    R.bx=R.ax;R.ax=0xA0
    R.logic(R.dx)
    if R.zero:
        R.bx,R.dx=R.dx,R.bx;R.al=0x90
        R.logic(R.dh,8)
        if R.zero:R.dl,R.dh=R.dh,R.dl;R.al=0x88
    R.logic(R.dx)
    while not R.sign:
        R.al=R.inc(R.al,8,-1)
        R.bx=R.add(R.bx,R.bx);R.dx=R.add(R.dx,R.dx,carry=R.carry)
    R.logic(R.ch,8)
    if not R.sign:R.dh=R.logic(R.dh&0x7F,8)


def to_long(R):                        # 0C37–0C92
    R.ax,R.bx=R.bx,R.ax;R.cl=0x9F
    R.cl=R.sub(R.cl,R.bx&255,8)
    if R.carry:return
    R.sub(R.cl,0x1F,8)
    if R.cl>0x1F:R.ax=R.logic(0);R.dx=R.logic(0);return
    R.cl=R.inc(R.cl,8);R.bx=(R.bx&255)|(R.dh<<8)
    R.dh=R.logic(R.dh|0x80,8)
    R.sub(R.cl,0x11,8)
    if R.cl>=0x11:
        R.ax=R.dx;R.dx=R.logic(0);R.cl=R.sub(R.cl,0x10,8)
    R.sub(R.cl,9,8)
    if R.cl>=9:
        R.al=R.ah;R.ah=R.dl;R.dl=R.dh;R.dh=R.logic(0,8);R.cl=R.sub(R.cl,8,8)
    while True:
        R.dx=R.shr(R.dx);R.ax=R.rcr(R.ax);R.cl=R.inc(R.cl,8,-1)
        if R.zero:break
    if R.carry:
        R.logic(R.ch,8)
        if not R.zero:
            R.ax=R.add(R.ax,1);R.dx=R.add(R.dx,0,carry=R.carry)
            if R.sign:R.flags|=CF;return
    R.logic(R.bx>>8,8)
    if R.sign:
        R.ax=~R.ax;R.dx=~R.dx;R.ax=R.add(R.ax,1);R.dx=R.add(R.dx,0,carry=R.carry)
    R.flags&=~CF


def round_add(R):                      # 09FC–0A1D
    R.ax=R.add(R.ax,0x80);R.bx=R.add(R.bx,0,carry=R.carry);R.dx=R.add(R.dx,0,carry=R.carry)
    if R.carry:
        R.dx=R.rcr(R.dx);R.cl=R.inc(R.cl,8)
        if R.zero:R.flags|=CF;return
    R.al=R.cl;R.dh=R.logic(R.dh&0x7F,8);R.dh=R.logic(R.dh|R.ch,8)


def add_real(R):                       # 098F–0A4F
    R.logic(R.cl,8)
    if R.zero:return
    R.logic(R.al,8)
    if R.zero:R.ax,R.bx,R.dx=R.cx,R.si,R.di;return
    R.sub(R.al,R.cl,8)
    if R.al>R.cl:R.ax,R.cx=R.cx,R.ax;R.bx,R.si=R.si,R.bx;R.dx,R.di=R.di,R.dx
    R.al=R.sub(R.al,R.cl,8);R.al=R.sub(0,R.al,8);R.sub(R.al,0x28,8)
    if R.al>=0x28:R.ax,R.bx,R.dx=R.cx,R.si,R.di;return
    R.cl,R.al=R.al,R.cl
    R.push(R.bp);R.push(R.ax)
    R.ah=R.dh;R.ah=R.logic(R.ah&0x80,8);R.bp=R.ax
    R.ax=R.logic(R.ax^R.di);R.ax=R.pop();R.push(R.flags)
    R.al=0;R.dh=R.logic(R.dh|0x80,8);R.di=R.logic(R.di|0x8000)
    while True:
        R.sub(R.cl,8,8)
        if R.cl<8:break
        R.al=R.ah;R.ah=R.bx&255;R.bx=((R.bx>>8)&255)|(R.dl<<8);R.dl=R.dh
        R.dh=R.logic(0,8);R.cl=R.sub(R.cl,8,8)
    R.logic(R.cl,8)
    if not R.zero:
        while True:
            R.dx=R.shr(R.dx);R.bx=R.rcr(R.bx);R.ax=R.rcr(R.ax);R.cl=R.inc(R.cl,8,-1)
            if R.zero:break
    R.flags=R.pop()
    subtract=R.sign
    if not subtract:
        R.ax=R.add(R.ax,R.cx);R.bx=R.add(R.bx,R.si,carry=R.carry);R.dx=R.add(R.dx,R.di,carry=R.carry)
        R.cx=R.bp;R.bp=R.pop()
        if R.carry:
            R.dx=R.rcr(R.dx);R.bx=R.rcr(R.bx);R.ax=R.rcr(R.ax);R.cl=R.inc(R.cl,8)
            if R.zero:R.flags|=CF;return
        round_add(R);return
    R.ax=R.sub(R.ax,R.cx);R.bx=R.sub(R.bx,R.si,carry=R.carry);R.dx=R.sub(R.dx,R.di,carry=R.carry)
    R.cx=R.bp;R.bp=R.pop()
    if R.carry:
        R.dx=~R.dx;R.bx=~R.bx;R.ax=R.sub(0,R.ax);R.flags^=CF
        R.bx=R.add(R.bx,0,carry=R.carry);R.dx=R.add(R.dx,0,carry=R.carry);R.ch=R.logic(R.ch^0x80,8)
    R.di=R.dx;R.di=R.logic(R.di|R.bx);R.di=R.logic(R.di|R.ax)
    if R.zero:return
    while True:
        R.logic(R.dh,8)
        if R.sign:round_add(R);return
        R.ax=R.shl(R.ax);R.bx=R.rcl(R.bx);R.dx=R.rcl(R.dx);R.cl=R.inc(R.cl,8,-1)
        if R.zero:zero(R);return


def round_product(R):                  # 0B35–0B56
    R.ax=R.add(R.ax,0x80);R.bx=R.add(R.bx,0,carry=R.carry);R.dx=R.add(R.dx,0,carry=R.carry)
    if R.carry:R.dx=R.rcr(R.dx);R.cx=R.inc(R.cx)
    R.logic(R.ch&0x40,8)
    if not R.zero:zero(R);return
    R.cx=R.inc(R.cx);R.al=R.cl;R.dh=R.logic(R.dh^R.ch,8);R.ch=R.shr(R.ch,8)


def multiply_real(R):                  # 0A52–0B56
    R.logic(R.al,8)
    if R.zero:zero(R);return
    R.logic(R.cl,8)
    if R.zero:zero(R);return
    R.push(R.bp);R.bp=R.dx
    R.dx=R.logic(R.dx^R.di);R.dx=R.logic(R.dx&0x8000)
    R.al,R.dl=R.dl,R.al;R.dl=R.add(R.dl,R.cl,8);R.dh=R.add(R.dh,R.al,8,R.carry);R.cl=R.al
    R.bp=R.logic(R.bp|0x8000);R.di=R.logic(R.di|0x8000);R.push(R.dx)
    R.logic(R.ah,8)
    simple=False
    if R.zero:
        R.logic(R.bx)
        simple=R.zero
    if not simple:
        R.logic(R.ch,8)
        if R.zero:
            R.logic(R.si)
            if R.zero:
                R.ax,R.cx=R.cx,R.ax;R.bx,R.si=R.si,R.bx;R.bp,R.di=R.di,R.bp
                simple=True
    if simple:
        R.ax=R.bp;R.al=R.ah;R.mul(R.al,R.ch,8);R.bx=R.ax
        R.ax=R.bp;R.mul(R.ax,R.si);R.bx=R.add(R.bx,R.ax);R.dx=R.add(R.dx,0,carry=R.carry);R.cx=R.dx
        R.ax=R.bp;R.mul(R.ax,R.di);R.ax=R.add(R.ax,R.cx);R.dx=R.add(R.dx,0,carry=R.carry)
    else:
        for value in (R.di,R.si,R.cx,R.bp,R.bx,R.ax):R.push(value)
        R.bp=R.sp;R.cx=R.logic(0);R.flush()
        def word(off):return R._mem.u16(R._mem.ss_lin(R.bp+off))
        R.al=R._mem.u8(R._mem.ss_lin(R.bp+1));R.mul(R.al,R._mem.u8(R._mem.ss_lin(R.bp+7)),8)
        R.si,R.di,R.bx=R.ax,R.cx,R.cx
        R.ax=word(0);R.mul(R.ax,word(8));R.si=R.add(R.si,R.ax);R.di=R.add(R.di,R.dx,carry=R.carry);R.bx=R.add(R.bx,R.cx,carry=R.carry)
        R.ax=word(2);R.mul(R.ax,word(6));R.si=R.add(R.si,R.ax);R.di=R.add(R.di,R.dx,carry=R.carry);R.bx=R.add(R.bx,R.cx,carry=R.carry)
        R.si=R.cx
        R.ax=word(0);R.mul(R.ax,word(10));R.di=R.add(R.di,R.ax);R.bx=R.add(R.bx,R.dx,carry=R.carry);R.si=R.add(R.si,R.cx,carry=R.carry)
        R.ax=word(2);R.mul(R.ax,word(8));R.di=R.add(R.di,R.ax);R.bx=R.add(R.bx,R.dx,carry=R.carry);R.si=R.add(R.si,R.cx,carry=R.carry)
        R.ax=word(4);R.mul(R.ax,word(6));R.di=R.add(R.di,R.ax);R.bx=R.add(R.bx,R.dx,carry=R.carry);R.si=R.add(R.si,R.cx,carry=R.carry)
        R.di=R.cx
        R.ax=word(2);R.mul(R.ax,word(10));R.bx=R.add(R.bx,R.ax);R.si=R.add(R.si,R.dx,carry=R.carry);R.di=R.add(R.di,R.cx,carry=R.carry)
        R.ax=word(4);R.mul(R.ax,word(8));R.bx=R.add(R.bx,R.ax);R.si=R.add(R.si,R.dx,carry=R.carry);R.di=R.add(R.di,R.cx,carry=R.carry)
        R.ax=word(4);R.mul(R.ax,word(10));R.ax=R.add(R.ax,R.si);R.dx=R.add(R.dx,R.di,carry=R.carry);R.sp=R.add(R.sp,12)
    R.ax,R.bx=R.bx,R.ax;R.cx=R.pop();R.bp=R.pop()
    R.logic(R.dh,8)
    if not R.sign:
        R.ax=R.shl(R.ax);R.bx=R.rcl(R.bx);R.dx=R.rcl(R.dx);R.cx=R.inc(R.cx,delta=-1)
    R.cx=R.sub(R.cx,0x8081)
    round_product(R)


def divide_real(R):                    # 0B57–0BCB, then 0B35
    R.logic(R.al,8)
    if R.zero:zero(R);return
    R.push(R.bp);R.bp=R.dx;R.dx=R.logic(R.dx^R.di)
    R.di=R.logic(R.di|0x8000);R.bp=R.logic(R.bp|0x8000);R.dx=R.logic(R.dx&0x8000)
    R.dl,R.al=R.al,R.dl;R.dl=R.sub(R.dl,R.cl,8);R.dh=R.sub(R.dh,R.al,8,R.carry);R.push(R.dx)
    R.al=2;R.dx=1
    compare=True
    while True:
        if compare:
            R.sub(R.bp,R.di)
            if R.zero:
                R.sub(R.bx,R.si)
                if R.zero:R.sub(R.ah,R.ch,8)
            if not R.carry:
                R.ah=R.sub(R.ah,R.ch,8);R.bx=R.sub(R.bx,R.si,carry=R.carry);R.bp=R.sub(R.bp,R.di,carry=R.carry)
        R.dx=R.rcl(R.dx)
        if R.carry:
            R.al=R.inc(R.al,8,-1)
            if R.sign:break
            R.push(R.dx);R.dx=1
            if R.zero:R.dl=0x40
        R.ah=R.shl(R.ah,8);R.bx=R.rcl(R.bx);R.bp=R.rcl(R.bp)
        compare=not R.carry
        if not compare:
            R.ah=R.sub(R.ah,R.ch,8);R.bx=R.sub(R.bx,R.si,carry=R.carry);R.bp=R.sub(R.bp,R.di,carry=R.carry)
            R.flags&=~CF
    R.ax=R.dx;R.cl=6
    for _ in range(6):R.ax=R.shl(R.ax)
    R.bx=R.pop();R.dx=R.pop();R.cx=R.pop();R.bp=R.pop()
    R.ax=~R.ax;R.bx=~R.bx;R.dx=R.logic(R.dx^0xFFFF)
    if not R.sign:
        R.ax=R.rcl(R.ax);R.bx=R.rcl(R.bx);R.dx=R.rcl(R.dx);R.cx=R.inc(R.cx,delta=-1)
    R.cx=R.add(R.cx,0x8080)
    round_product(R)


def near(R,return_ip,core):
    R.push(return_ip)
    core(R)
    R.sp+=2


def runtime_error(R,code):
    R.ax=code
    R.store()
    raise PortError(f'original real runtime error {code} at 23E4:00D1')


@PORTS.port('23E4:0CB9',ret='retf')
def long_to_real(mem,variant):
    R=RealRegs(mem);near(R,0x0CBC,from_long);R.store()


@PORTS.port('23E4:0CC5',ret='retf')
def real_to_long(mem,variant):
    R=RealRegs(mem);R.ch=1;near(R,0x0CCA,to_long)
    if R.carry:runtime_error(R,0xCF)
    R.store()


@PORTS.port('23E4:0C93',ret='retf')
def real_add(mem,variant):
    R=RealRegs(mem);near(R,0x0C96,add_real)
    if R.carry:runtime_error(R,0xCD)
    R.store()


@PORTS.port('23E4:0CA5',ret='retf')
def real_multiply(mem,variant):
    R=RealRegs(mem);near(R,0x0CA8,multiply_real)
    if R.carry:runtime_error(R,0xCD)
    R.store()


@PORTS.port('23E4:0CAB',ret='retf')
def real_divide(mem,variant):
    R=RealRegs(mem);R.logic(R.cl,8)
    if R.zero:runtime_error(R,0xC8)
    near(R,0x0CB2,divide_real)
    if R.carry:runtime_error(R,0xCD)
    R.store()


def coefficient(R,word):
    """A word in the source's CS coefficient tables (the 16-bit offset wraps)."""
    return R._mem.u16(R._mem.seg(0x23E4)*16+(word&MASK))


def polynomial(R):                     # 1101–114F, including the loop at111F
    R.enter(6)
    R.local16(-6,R.ax);R.local16(-4,R.bx);R.local16(-2,R.dx)
    R.ax=coefficient(R,R.di);R.bx=coefficient(R,R.di+2);R.dx=coefficient(R,R.di+4)
    first=True
    while True:
        R.push(R.cx);R.push(R.di)
        if not first:
            R.cx=coefficient(R,R.di);R.si=coefficient(R,R.di+2);R.di=coefficient(R,R.di+4)
            near(R,0x112F,add_real)
        first=False
        R.flush()
        R.cx=R._mem.u16(R._mem.ss_lin(R.bp-6));R.si=R._mem.u16(R._mem.ss_lin(R.bp-4));R.di=R._mem.u16(R._mem.ss_lin(R.bp-2))
        near(R,0x113B,multiply_real)
        R.di=R.pop();R.cx=R.pop();R.di=R.add(R.di,6)
        R.cx-=1                        # LOOP preserves flags
        if R.cx==0:break
    R.cx=0x81;R.si=R.logic(0);R.di=R.logic(0)
    near(R,0x114C,add_real)
    R.leave()


def odd_polynomial(R):                 # 10E8–1100, tail-jumps to0A52
    for value in (R.dx,R.bx,R.ax,R.cx,R.di):R.push(value)
    R.cx,R.si,R.di=R.ax,R.bx,R.dx
    near(R,0x10F6,multiply_real)
    R.di=R.pop();R.cx=R.pop()
    near(R,0x10FB,polynomial)
    R.cx=R.pop();R.si=R.pop();R.di=R.pop()
    multiply_real(R)


def add_preserved(R):                  # 0CDF–0CE8
    for value in (R.di,R.si,R.cx):R.push(value)
    near(R,0x0CE5,add_real)
    R.cx=R.pop();R.si=R.pop();R.di=R.pop()


def subtract_real(R):                  # 098B falls through to098F
    R.di=R.logic(R.di^0x8000)
    add_real(R)


@PORTS.port('23E4:0E67',ret='retf')
def real_logarithm(mem,variant):
    """0E67–0EEB: source normalization, odd polynomial, and exponent correction."""
    R=RealRegs(mem)
    R.logic(R.al,8)
    if R.zero:runtime_error(R,0xCF)
    R.logic(R.dh&0x80,8)
    if not R.zero:runtime_error(R,0xCF)
    R.cl=0x81;R.al=R.sub(R.al,R.cl,8);R.push(R.ax);R.al=R.cl
    R.cx,R.si,R.di=0xFB80,0xF333,0x3504
    near(R,0x0E89,multiply_real)
    R.cx,R.si,R.di=R.ax,R.bx,R.dx
    R.ax=0x81;R.bx=R.logic(0);R.dx=R.logic(0)
    near(R,0x0E99,add_preserved)
    for value in (R.dx,R.bx,R.ax):R.push(value)
    R.ax=0x81;R.bx=R.logic(0);R.dx=0x8000
    near(R,0x0EA7,add_real)
    R.cx=R.pop();R.si=R.pop();R.di=R.pop()
    near(R,0x0EAD,divide_real)
    R.di,R.cx=0x0EEC,6
    near(R,0x0EB6,odd_polynomial)
    R.al=R.inc(R.al,8)
    R.cx,R.si,R.di=0xD27F,0x17F7,0x3172
    near(R,0x0EC4,add_real)
    R.cx=R.pop()
    for value in (R.dx,R.bx,R.ax):R.push(value)
    R.al=R.cl;R.ax=R.al-256 if R.al&128 else R.al;R.dx=0xFFFF if R.ax&0x8000 else 0
    near(R,0x0ECF,from_long)
    R.cx,R.si,R.di=0xD280,0x17F7,0x3172
    near(R,0x0EDB,multiply_real)
    R.cx=R.pop();R.si=R.pop();R.di=R.pop()
    near(R,0x0EE1,add_real)
    R.sub(R.al,0x67,8)
    if R.al<0x67:zero(R)
    R.store()


@PORTS.port('23E4:0F10',ret='retf')
def real_exponential(mem,variant):
    """0F10–0F82: saved sign, integer/fraction split, source polynomial and scale."""
    R=RealRegs(mem)
    R.logic(R.dh&0x80,8);R.push(R.flags)
    R.dh=R.logic(R.dh&0x7F,8)
    R.cx,R.si,R.di=0xD280,0x17F7,0x3172
    near(R,0x0F23,divide_real)
    R.sub(R.al,0x88,8)
    if R.al>=0x88:
        R.ax=R.pop();runtime_error(R,0xCD)
    for value in (R.dx,R.bx,R.ax):R.push(value)
    R.al=R.inc(R.al,8);R.ch=0xFF
    near(R,0x0F31,to_long)
    R.cx=R.pop();R.si=R.pop();R.di=R.pop()
    R.push(R.ax);R.push(R.cx)
    near(R,0x0F39,from_long)
    R.cx=R.pop();R.logic(R.al,8)
    if not R.zero:R.al=R.inc(R.al,8,-1)
    R.ax,R.cx=R.cx,R.ax;R.bx,R.si=R.si,R.bx;R.dx,R.di=R.di,R.dx
    near(R,0x0F48,subtract_real)
    R.di,R.cx=0x0F83,8
    near(R,0x0F51,polynomial)
    R.cx=R.pop();R.cx=R.shr(R.cx)
    if R.carry:
        R.push(R.cx);R.cx,R.si,R.di=0xFB81,0xF333,0x3504
        near(R,0x0F63,multiply_real)
        R.cx=R.pop()
    R.al=R.add(R.al,R.cl,8)
    if R.carry:
        R.ax=R.pop();runtime_error(R,0xCD)
    R.flags=R.pop()
    if not R.zero:
        R.cx,R.si,R.di=R.ax,R.bx,R.dx
        R.ax=0x81;R.bx=R.logic(0);R.dx=R.logic(0)
        near(R,0x0F7B,divide_real)
    R.store()
