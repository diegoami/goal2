"""[designed: #266 owner rework] Original-first static desktop illustrations.

Authoring only: no game modules, runtime, original assets or executable UI.
Pillow measures authored DejaVu Sans Mono text; Inkscape exports SVG to PNG.
--check regenerates in a temporary directory and compares retained bytes.
"""
from pathlib import Path
from collections import Counter
import argparse
import html
import json
import os
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from PIL import ImageFont

ROOT = Path(__file__).resolve().parent
D = json.loads((ROOT / 'scenario.json').read_text())
P = {p['key']: p for p in D['players']}
BLACK, WHITE, GREY = '#000000', '#eeeeee', '#aaaaaa'
RED, CYAN, YELLOW = '#ff5555', '#55ffff', '#ffff55'
GREEN, MAGENTA, GOLD = '#55ff55', '#ff55ff', '#ffbb33'
EDGE, EMPTY = '#777777', '#9b009b'
ROLE_COLORS = {'GK': GREEN, 'SW': RED, 'CB': RED, 'LB': RED, 'RB': RED, 'MF': CYAN, 'FW': YELLOW}
ROLE_NAMES = {'GK':'Goalkeeper','SW':'Sweeper','CB':'Centre back','LB':'Left back','RB':'Right back','MF':'Midfield','FW':'Forward'}
SKILLS = ['Keeping', 'Kicking', 'Tackling', 'Heading', 'Marking', 'Passing',
          'Crossing', 'Feinting', 'Control', 'Dribbling', 'Shooting', 'Penalties']
CHARS = ['Hardness', 'Fitness', 'Energy', 'Morale', 'Leadership']
FONTS = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in FONTS:
        suffix = '-Bold' if bold else ''
        FONTS[key] = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono'+suffix+'.ttf', size)
    return FONTS[key]


class Sheet:
    def __init__(self, number, title, *, active='Country', focus=False, small=False, match=False, startup=False):
        self.number = number
        self.w, self.h = (900, 640) if small else (1440, 900)
        self.small, self.focus, self.match = small, focus, match
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">',
                      f'<title>{html.escape(title)}</title><desc>Designed original-first native desktop target. Fictional story. Not a current-build capture.</desc>']
        self.bounds, self.bars = [], []
        self.rect(0, 0, self.w, self.h, BLACK)
        self.text(8, 17, f'{number:02} TARGET ILLUSTRATION / FICTIONAL DATA / DESKTOP / NOT CURRENT BUILD', 14, GREY)
        self.x, self.y = (20, 102) if focus else (178, 174)
        if match:
            return
        if startup:
            self.text(20,73,'GOAL2 / START OR RESUME',36,CYAN,True)
            self.text(20,137,title,30,RED,True)
            return
        if focus:
            self.text(20, 56, title, 26 if small else 32, YELLOW, True)
            self.text(self.w-288 if not small else 614, 55, '[Menu >] [Top v]', 18, CYAN)
            context = {4:'HOLLAND / ALEX / 2030 / POOL EXCHANGE',
                       7:'HOLLAND / ALEX / 2030 / HALF-TIME',
                       11:'HOLLAND / 2030 / [Roster] [PLAYER *] [Tactics]',
                       17:'HOLLAND / 2030 / [ROSTER *] [Player] [Tactics]',
                       18:'HOLLAND / ALEX / 2032 / SQUAD UPDATE'}.get(number,'HOLLAND / ALEX / 2030 / TEAM')
            self.text(20,85,context,18,CYAN)
        else:
            self.parts.append('<g data-chrome="top">')
            self.box(8, 27, self.w-16, 79, CYAN)
            self.text(24, 63, 'GOAL2', 34, CYAN, True)
            self.text(178, 61, 'HOLLAND', 30, YELLOW, True)
            self.text(178, 91, 'Alex / 2032 / Career archive' if number in (10,19) else 'Alex / 2030 / World qualifying', 20, WHITE)
            context={8:('Result: Holland 2-1 Belgium','Friendly / Half-time 1-1'),
                     9:('Next: Holland v Eire','Qualifying / Belgium friendly completed'),
                     10:('Country career archive','Completed 2030 / Next cycle 2032'),
                     19:('Completed World Cup 2030','Archive / Next cycle 2032'),
                     12:('Holland / same career','Alternative save and fixture states'),
                     13:('Hypothetical knockout','Later branch / not the Belgium friendly'),
                     15:('Match: Holland v Belgium','Friendly at home / first half')}.get(number,('Next: Holland v Belgium','Friendly at home'))
            self.text(728, 60, context[0], 25, CYAN, True)
            self.text(728, 91, context[1], 20, WHITE)
            self.text(1220, 91, '[Top ^]', 20, CYAN)
            self.parts.append('</g><g data-chrome="side">')
            self.box(8, 118, 150, 754, CYAN)
            self.text(17, 145, '[< Hide]', 20, CYAN)
            for i, item in enumerate(['Country', 'Team', 'Fixtures', 'Match', 'History', 'Save']):
                yy=205+i*68
                if item==active:
                    self.rect(14, yy-25, 138, 38, GREY)
                self.text(22, yy, item, 21, BLACK if item==active else CYAN, True)
            self.text(20, 844, 'F1 Help', 20, CYAN)
            self.parts.append('</g>')
            self.text(178, 147, title, 30, RED, True)

    def rect(self, x, y, w, h, fill=BLACK, stroke=None, *, kind=None):
        assert x>=0 and y>=0 and w>0 and h>0 and x+w<=self.w and y+h<=self.h, (x,y,w,h)
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"'+(f' stroke="{stroke}"' if stroke else '')+(f' data-kind="{kind}"' if kind else '')+'/>')

    def text(self, x, y, value, size=22, fill=WHITE, bold=False, width=None):
        value=str(value); measured=font(size,bold).getlength(value)
        assert x>=0 and y-size>=0 and x+measured<=self.w-5 and y+4<=self.h, (value,x,y,measured)
        if width is not None: assert measured<=width, (value,measured,width)
        self.bounds.append((value,x,y,size,measured))
        self.parts.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans Mono" font-size="{size}" font-weight="{700 if bold else 400}" fill="{fill}" xml:space="preserve">{html.escape(value)}</text>')

    def lines(self, x, y, values, size=22, step=34, fill=WHITE, width=None):
        for i, value in enumerate(values): self.text(x,y+i*step,value,size,fill,width=width)

    def box(self, x, y, w, h, color=EDGE, label=None):
        self.rect(x,y,w,h,BLACK,color)
        if label:
            self.rect(x+13,y-1,min(w-26,len(label)*14+14),28,BLACK)
            self.text(x+18,y+20,label,22,color,True,width=w-32)

    def button(self, x, y, label, w=260, selected=False, disabled=False):
        fill=GREY if selected else BLACK
        color=GREY if disabled else CYAN
        self.rect(x,y,w,44,fill,color)
        self.text(x+12,y+30,label,22,BLACK if selected else color,True,width=w-24)

    def bar(self, x, y, width, slots, filled, label, raw, *, size=20, label_width=135):
        self.parts.append(f'<g data-attribute="{html.escape(label)}" data-slots="{slots}" data-filled="{filled}">')
        self.text(x,y,label,size,GOLD,True,width=label_width-4)
        bar_x=x+label_width
        bar_w=width-label_width-44
        assert bar_w>=60 and 0<=filled<=slots
        for i in range(slots):
            step=bar_w/slots
            self.rect(bar_x+i*step,y-size+4,max(1,step-2),size-3,WHITE if i<filled else EMPTY)
        self.parts.append('<g data-raw="value">')
        self.text(x+width-38,y,raw,size,WHITE,True,width=38)
        self.parts.append('</g>')
        self.parts.append('</g>')
        self.bars.append((label,raw,slots,filled,bar_w))

    def card(self, x, y, key, w, h=632, *, compact=False, context='BENCH / READY', snapshot='players', expanded=False):
        p=profile(key,snapshot); size=18 if compact else (22 if w>=780 else 20)
        row=23 if compact else (34 if expanded else 28)
        self.parts.append(f'<g data-player="{key}" data-snapshot="{snapshot}">')
        self.box(x,y,w,h,RED)
        self.text(x+14,y+32,p['name'].upper(),26 if compact else 30,ROLE_COLORS[p['role']],True)
        self.text(x+w-85,y+32,p['role'],26 if compact else 30,ROLE_COLORS[p['role']],True)
        self.text(x+14,y+62,f"Age {p['age']} / Caps {p['caps']} / Goals {p['goals']}",size,WHITE)
        self.text(x+14,y+87,f"{p['height']} / {p['foot']} foot / {context}",size,GREEN)
        self.text(x+14,y+112,f"National {ROLE_NAMES[p['national_position']]} / Club {ROLE_NAMES[p['club_position']]}",size,WHITE)
        self.text(x+14,y+137,'Cards: none / Performance: not recorded'+(' / Words illustrative' if compact else ''),size,WHITE)
        start=y+(157 if compact else 172)
        gap=26; half=(w-28-gap)/2
        for i,(name,val) in enumerate(zip(SKILLS,p['skills'])):
            self.bar(x+14,start+i*row,half,25,val,name,val,size=size,label_width=124 if not compact else 116)
        # [confirmed: T84 field contract F008/F018/F019] Illustrative decoded
        # values, using the established 14-cell characteristic bar formulas.
        chars=[('Hardness',p['hardness'],p['hardness']*14//16),('Fitness',p['fitness'],p['fitness']*14//32),
               ('Energy',p['energy'],p['energy']*14//32),('Morale',p['morale'],p['morale']*14//32),
               ('Leadership',p['leadership'],p['leadership']*14//7)]
        right=x+14+half+gap
        right_label=148 if size==22 else (132 if not compact else 122)
        char_row=37 if compact else 43
        for i,(name,raw,filled) in enumerate(chars):
            yy=start+i*char_row
            self.bar(right,yy,half,14,filled,name,raw,size=size,label_width=right_label)
            self.parts.append(f'<g data-descriptor="{name}">')
            self.text(right+right_label,yy+(18 if compact else 22),p['descriptors'][name],18,GREEN)
            self.parts.append('</g>')
        tactics_y=start+5*char_row+(10 if compact else 8)
        self.text(right,tactics_y,'TACTICS / T=TEAM',size,RED,True)
        tactic_row=20 if compact else 28
        for i,name in enumerate(['Position','Possession','Passing','Tackling','Mark']):
            yy=tactics_y+(i+1)*tactic_row
            self.text(right,yy,name,size,GOLD)
            suffix='' if p['tactics'][name]=='Not applicable' else ' T'
            self.text(right+right_label,yy,p['tactics'][name]+suffix,18,GREEN,width=half-right_label)
        if not compact:
            self.text(x+14,y+h-17,'Original units / descriptor words illustrative',15,MAGENTA)
        self.parts.append('</g>')

    def roster(self, x, y, keys, xi, *, wide=False, row=28, selected='NL14'):
        self.text(x,y,'SQUAD 20 / XI 11 / BENCH 9',21,CYAN,True)
        for i,k in enumerate(keys):
            yy=y+38+i*row
            self.parts.append(f'<g data-roster="{k}">')
            if k==selected: self.rect(x-4,yy-22,400 if wide else 356,27,GREY)
            selected_color=BLACK if k==selected else ROLE_COLORS[P[k]['role']]
            self.text(x,yy,'+' if k in xi else '-',24,selected_color)
            self.text(x+24,yy,P[k]['name'],24,selected_color,True)
            self.text(x+277,yy,P[k]['role']+(' C' if k==D['captain'] else ''),24,selected_color,True)
            self.parts.append('</g>')

    def footer(self, value):
        self.text(20 if self.focus or self.match else 178,self.h-15,value,18,MAGENTA)

    def save(self, directory, slug):
        count={3:1,4:2,7:2,11:1,14:1,18:2}.get(self.number,0)
        if count:
            labels=Counter(b[0] for b in self.bars)
            assert all(labels[name]==count for name in SKILLS+CHARS), (slug,labels)
        if self.number in (3,14):
            assert all(any(P[k]['name'] in b[0] for b in self.bounds) for k in D['initial_squad'])
        if self.number==6:
            assert self.pitch_fraction>=0.82 and self.visible_commentary_lines==2
        path=directory/(slug+'.svg')
        svg='\n'.join(self.parts+['</svg>'])+'\n'
        check_svg(svg,self.number)
        path.write_text(svg)
        return path, len(self.bounds), len(self.bars)


def profile(key, snapshot='players'):
    return P[key] if snapshot=='players' else D[snapshot][key]


def check_svg(svg, number):
    """[designed] Inspect actual SVG geometry and text against fictional source data.

    This bounds the authored composition, not native UI or general SVG security.
    Expected domains/formulas: T84 F008/F018/F019 contract, cited in evidence.md.
    """
    root=ET.fromstring(svg); ns={'s':'http://www.w3.org/2000/svg'}
    width,height=float(root.attrib['width']),float(root.attrib['height'])
    def visible(el):
        assert el.get('opacity','1')=='1' and el.get('display','inline')!='none'
        assert el.get('visibility','visible')=='visible' and 'style' not in el.attrib
    for el in root.iter(): visible(el)
    for rect in root.findall('.//s:rect',ns):
        x,y,w,h=[float(rect.get(k,'0')) for k in ('x','y','width','height')]
        assert x>=0 and y>=0 and w>0 and h>0 and x+w<=width and y+h<=height, 'Invisible/outside rectangle'
    groups=root.findall('.//s:g',ns)
    cards=[g for g in groups if 'data-player' in g.attrib]
    expected={3:[('NL14','players')],4:[('NL20','players'),('NL21','players')],
              7:[('NL08','halftime_profiles'),('NL14','halftime_profiles')],
              11:[('NL14','players')],14:[('NL14','players')],
              18:[('NL08','later_profiles'),('NL22','later_profiles')]}.get(number,[])
    assert [(g.get('data-player'),g.get('data-snapshot')) for g in cards]==expected
    bars=[g for g in groups if 'data-attribute' in g.attrib]
    assert len(bars)==17*len(expected)
    for card in cards:
        p=profile(card.get('data-player'),card.get('data-snapshot'))
        card_bars=card.findall('s:g[@data-attribute]',ns)
        assert Counter(g.get('data-attribute') for g in card_bars)==Counter(SKILLS+CHARS)
        for group in card_bars:
            name=group.attrib['data-attribute']
            raw_text=group.find('s:g[@data-raw="value"]/s:text',ns)
            assert raw_text is not None
            raw=int(raw_text.text)
            source=p['skills'][SKILLS.index(name)] if name in SKILLS else p[name.lower()]
            assert raw==source, 'Printed value disagrees with scenario'
            slots=25 if name in SKILLS else 14
            divisor={'Hardness':16,'Fitness':32,'Energy':32,'Morale':32,'Leadership':7}
            filled=raw if name in SKILLS else raw*14//divisor[name]
            assert int(group.get('data-slots'))==slots and int(group.get('data-filled'))==filled
            rects=group.findall('s:rect',ns)
            assert len(rects)==slots, 'Missing segmented bar'
            previous=None
            for i,rect in enumerate(rects):
                x,y,w,h=[float(rect.get(k,'0')) for k in ('x','y','width','height')]
                assert w>=1 and h>=12, 'Bar segments must have visible area'
                assert rect.get('fill')==(WHITE if i<filled else EMPTY), 'Bar/value mismatch'
                assert rect.get('fill-opacity','1')=='1'
                if previous:
                    px,py,pw,ph=previous
                    assert 0<=x-px-pw<=3 and y==py and h==ph, 'Segments overlap or drift'
                previous=x,y,w,h
            assert all(float(t.get('font-size'))>=18 for t in group.findall('.//s:text',ns))
        descriptors=card.findall('s:g[@data-descriptor]',ns)
        assert Counter(g.get('data-descriptor') for g in descriptors)==Counter(CHARS)
        for group in descriptors:
            assert group.find('s:text',ns).text==p['descriptors'][group.get('data-descriptor')], 'Missing characteristic descriptor'
    for row in [g for g in groups if 'data-roster' in g.attrib]:
        p=P[row.get('data-roster')]
        name=next(t for t in row.findall('s:text',ns) if t.text==p['name'])
        backgrounds=row.findall('s:rect',ns)
        background=backgrounds[0].get('fill') if backgrounds else BLACK
        assert name.get('fill')!=background, 'Roster name is invisible on background'
        assert name.get('fill')==(BLACK if backgrounds else ROLE_COLORS[p['role']])
        assert float(name.get('font-size'))>=24
    if number in (3,14):
        assert {g.get('data-roster') for g in groups if 'data-roster' in g.attrib}==set(D['initial_squad'])
    chrome={g.attrib['data-chrome'] for g in groups if 'data-chrome' in g.attrib}
    if number in (1,6,11,14,17,18): assert not chrome
    if number in (3,15): assert chrome=={'top','side'}
    if number==6:
        field=root.find('.//s:rect[@data-kind="playing-field"]',ns)
        assert field is not None
        assert float(field.get('width'))*float(field.get('height'))/(width*height)>=.82, 'Playing field below 82%'
        recent=next(g for g in groups if g.attrib.get('data-commentary')=='recent')
        assert len(recent.findall('s:text',ns))==2


def validate_scenario():
    assert len(P)==22 and len(D['initial_squad'])==20 and len(set(D['initial_squad']))==20
    assert len(D['xi'])==11 and set(D['xi'])<=set(D['initial_squad']) and D['captain'] in D['xi']
    # [designed] The authored 4–4–2 must match the displayed starting roles.
    roles=[P[k]['role'] for k in D['xi']]
    assert roles.count('GK')==1 and sum(r in ('LB','RB','CB','SW') for r in roles)==4
    assert roles.count('MF')==4 and roles.count('FW')==2
    ex=D['pool_exchange']; assert ex['out'] not in D['xi'] and ex['in'] not in D['initial_squad']
    squad=[ex['in'] if k==ex['out'] else k for k in D['initial_squad']]
    sub=D['halftime_exchange']; assert sub['out'] in D['xi'] and sub['in'] in squad and sub['in'] not in D['xi']
    xi=[sub['in'] if k==sub['out'] else k for k in D['xi']]
    for p in list(P.values())+list(D['halftime_profiles'].values())+list(D['later_profiles'].values()):
        assert len(p['skills'])==12 and all(0<=v<=25 for v in p['skills'])
        assert 0<=p['hardness']<=16 and 0<p['fitness']<=32 and 0<p['energy']<=32
        assert 0<=p['morale']<32 and 0<=p['leadership']<=7
        assert set(p['descriptors'])==set(CHARS)
    assert len({tuple(p['skills']) for p in P.values()})==len(P), 'Cloned profiles'
    assert all(P[k]['skills'][0]>=20 for k in ('NL01','NL12'))
    assert P['NL21']['skills'][6:7]+P['NL21']['skills'][10:11]==[20,18]
    assert P['NL20']['skills'][6:7]+P['NL20']['skills'][10:11]==[16,12]
    assert D['halftime_profiles']['NL08']['energy']<D['halftime_profiles']['NL14']['energy']
    assert D['later_profiles']['NL08']['age']==P['NL08']['age']+2
    assert D['later_profiles']['NL08']['availability']=='Retired'
    assert sum(n for _,n in D['career_scorers'])==sum(m[3] for m in D['career_matches'])
    def score(t): return [sum(e['side']==s and e['minute']<=t for e in D['events']) for s in ['Holland','Belgium']]
    assert score(38)==[1,0] and score(45)==D['halftime_score'] and score(90)==D['final_score']
    assert all(e.get('player') in (D['xi'] if e['minute']<=45 else xi) for e in D['events'] if e['side']=='Holland')
    assert len(D['belgium_xi'])==11 and Counter(p['role'] for p in D['belgium_xi'])==Counter(roles)
    # [designed] This renderer draws a fixed story, not arbitrary simulation data.
    # Reject drift between the explicit prose/image chronology and the scenario.
    assert [(e['minute'],e['side'],P[e['player']]['name'] if 'player' in e else e['name']) for e in D['events']] == [(18,'Holland','D Vermeer'),(42,'Belgium','L Laurent'),(68,'Holland','N Smit')]
    assert (P[ex['out']]['name'],P[ex['in']]['name']) == ('C de Wit','R Noor')
    assert (P[sub['out']]['name'],P[sub['in']]['name']) == ('P Bos','J Jansen')
    assert P[D['captain']]['name']=='L de Boer' and D['next_opponent']=='Eire'
    return squad,xi



def team_sheet(number, *, focus=False, small=False):
    s=Sheet(number,'SELECT YOUR TEAM',active='Team',focus=focus,small=small)
    if small:
        s.card(20,103,'NL14',860,h=468,compact=True,context='BENCH / READY')
        s.button(20,584,'Roster 20 >',220)
        s.button(258,584,'Confirm team',240)
        s.button(516,584,'Discard',190)
        return s
    x,y=s.x,s.y
    s.box(x,y,414,704 if focus else 632,CYAN)
    s.roster(x+14,y+30,D['initial_squad'],D['xi'],row=31 if focus else 28)
    card_x=x+432; card_w=s.w-card_x-18
    s.card(card_x,y,'NL14',card_w,h=704 if focus else 632,expanded=focus)
    s.button(x,824,'Pool / Compare',240)
    s.button(x+258,824,'Attribute table',250)
    s.button(x+526,824,'Team tactics',240)
    s.button(x+784,824,'Confirm team',250)
    s.footer('Arrows: select / Tab: move / Enter: confirm / F11: '+('restore' if focus else 'hide')+' top + side bars')
    return s


def pitch(s, x, y, w, h):
    s.parts.append('<g data-pitch="schematic">')
    s.rect(x,y,w,h,'#062706')
    s.rect(x+9,y+9,w-18,h-18,BLACK,GREY,kind='playing-field')
    mid=x+w/2; top=y+9; bottom=y+h-9; cy=y+h/2
    s.parts.append(f'<path d="M{mid} {top} V{bottom}" stroke="{GREY}" fill="none"/><circle cx="{mid}" cy="{cy}" r="{h*.13}" stroke="{GREY}" fill="none"/>')
    for side in [0,1]:
        bx=x+9 if side==0 else x+w-9-w*.15
        s.rect(bx,y+h*.27,w*.15,h*.46,BLACK,GREY)
        gx=x+9 if side==0 else x+w-9-w*.06
        s.rect(gx,y+h*.40,w*.06,h*.20,BLACK,GREY)
    spots=[(.06,.5),(.21,.17),(.20,.39),(.23,.63),(.18,.83),(.41,.12),(.39,.35),(.42,.61),(.38,.86),(.60,.24),(.63,.70)]
    for side,color in [(0,GOLD),(1,WHITE)]:
        for i,(px,py) in enumerate(spots):
            if side: px=1-px; py=min(.94,py+.04)
            xx=x+w*px; yy=y+h*py
            role=P[D['xi'][i]]['role'] if side==0 else D['belgium_xi'][i]['role']
            s.text(xx,yy,role,26 if w<1100 else 32,color,True)
    s.parts.append(f'<circle cx="{mid+31}" cy="{cy-20}" r="6" fill="white"/>')
    s.parts.append('</g>')
    s.pitch_fraction=(w-18)*(h-18)/(s.w*s.h)


def streak(kind, venue):
    """[designed] Arithmetic over the fictional completed 2030 ledger only."""
    now=top=0
    for _,where,_,gf,ga in D['career_matches']:
        if venue is not None and where!=venue: continue
        result='W' if gf>ga else 'L' if gf<ga else 'D'
        continues=(result!=kind[3:]) if kind.startswith('not') else result==kind
        now=now+1 if continues else 0
        top=max(top,now)
    return now,top


def draw(directory):
    squad,second_xi=validate_scenario()
    exports=[]
    def keep(s,slug): exports.append(s.save(directory,slug))

    s=Sheet(1,'RETURN TO YOUR COUNTRY',startup=True)
    s.box(178,174,720,598,RED,'SAVED CAREER')
    s.text(204,266,'HOLLAND',60,YELLOW,True)
    s.lines(204,321,['MANAGER   Alex','CAMPAIGN  2030 World qualifying','NEXT      Belgium / Friendly / Home','THEN      Eire / Qualifying','SAVE      Before Belgium','TEAM      Confirmed / 20 players'],24,51)
    s.button(204,668,'RESUME HOLLAND',430,selected=True)
    s.box(920,174,502,598,CYAN,'NEW GAME')
    s.text(942,245,'CHOOSE YOUR COUNTRY',27,YELLOW,True)
    s.lines(942,301,['Holland       World 14','Belgium       World  8','Denmark       World  4','Eire          World 24'],24,45,fill=GREEN)
    s.button(942,515,'New career >',440)
    s.button(942,584,'Open another save',440)
    s.lines(942,695,['One manager first.','Review before starting.'],21,33,fill=MAGENTA)
    s.footer('Arrows: choose / Enter: accept / Esc: back / Existing saves stay yours')
    keep(s,'01-start-resume')

    s=Sheet(2,'WORLD CUP 2030 / QUALIFYING')
    s.box(178,174,390,221,RED,'YOUR COUNTRY')
    s.lines(198,236,['HOLLAND','Manager  Alex','World    14','Europe    3'],27,43,fill=WHITE)
    s.box(178,416,390,228,RED,'NEXT OPPONENT')
    s.text(198,483,'BELGIUM',32,RED,True)
    s.lines(198,531,['World     8','Europe    9','Friendly / Home'],25,41)
    s.box(178,665,390,141,CYAN,'YOUR CAMPAIGN')
    s.lines(198,717,['Group F / Played 0','Next qualifier: Eire'],23,42,fill=YELLOW)
    for yy,label in [(187,'Country info'),(266,'Fixture list'),(345,'Tournament'),(424,'History'),(503,'Select squad'),(582,'Prepare Belgium')]:
        s.button(590,yy,label,390,selected=label=='Select squad')
    s.text(594,708,'20 ready / XI 11',25,GREEN,True)
    s.text(594,751,'Captain: L de Boer',24,YELLOW)
    s.box(1000,174,422,632,CYAN)
    s.roster(1015,204,D['initial_squad'],D['xi'])
    s.footer('F1 Help / F7 Save / All ranks are illustrative / Top + side bars: retract')
    keep(s,'02-country-desk')

    keep(team_sheet(3),'03-team')

    s=Sheet(4,'NATIONAL POOL / COMPARE BOTH PLAYERS',active='Team',focus=True)
    s.card(20,108,'NL20',690,h=640,context='OUT / BENCH / READY')
    s.card(730,108,'NL21',690,h=640,context='IN / POOL / READY')
    s.text(20,790,'POOL 80 / 1–7: Noor Groen Hermans van Vliet Jonker Maas Bosman  [Browse >]',21,CYAN)
    s.button(20,818,'Confirm de Wit > Noor',460)
    s.button(500,818,'Cancel',200)
    s.text(732,849,'XI unchanged / one bench place',23,GREEN,True)
    s.footer('Both full cards stay pinned while browsing / Same original-unit bars')
    keep(s,'04-pool')

    s=Sheet(5,'HOLLAND v BELGIUM / FRIENDLY',active='Match')
    for x,title,names in [(178,'HOLLAND / 4-4-2',[dict(P[k],name=P[k]['name']+(' C' if k==D['captain'] else '')) for k in D['xi']]),(594,'BELGIUM / 4-4-2',D['belgium_xi'])]:
        s.box(x,174,390,620,CYAN,title)
        for i,name in enumerate(names):
            color=ROLE_COLORS[name['role']]
            s.text(x+18,239+i*43,name['name'],24,color,True)
        s.button(x+14,725,'Players / tactics',360)
    s.box(1010,174,412,620,RED,'PLAY')
    s.lines(1030,248,['QUICK RESULT','No watched pitch.','Decisions may pause.'],24,37,fill=WHITE)
    s.button(1030,359,'Start Quick',370)
    s.lines(1030,470,['WATCH MATCH','Follow the pitch.','Friendly: view-only.'],24,37,fill=WHITE)
    s.button(1030,579,'Start Watch',370,selected=True)
    s.text(1030,682,'SPEED: Normal',26,YELLOW,True)
    s.text(1030,729,'Slow / Normal / Fast',21,CYAN)
    s.text(1030,771,'Set before kickoff.',21,MAGENTA)
    s.footer('Noor on bench / Quick and Watch may differ / Confirm changes before Start')
    keep(s,'05-preparation')

    s=Sheet(6,'Holland 1-0 Belgium / 38 minutes / default pitch focus',match=True,focus=True)
    pitch(s,8,63,1424,776)
    s.rect(0,23,1440,40,BLACK)
    s.text(18,53,'HOLLAND',28,GOLD,True)
    s.text(162,53,'1 - 0',28,CYAN,True)
    s.text(280,53,'BELGIUM',28,WHITE,True)
    s.text(470,53,'38′ FIRST HALF / FRIENDLY',24,CYAN,True)
    s.text(1056,51,'[Menu >] [Top v]',22,MAGENTA)
    s.rect(8,840,1424,60,BLACK)
    s.parts.append('<g data-commentary="recent">')
    s.text(20,863,'35′ Belgium builds an attack',22,YELLOW)
    s.text(20,892,'38′ Play continues',22,CYAN)
    s.parts.append('</g>')
    s.text(1020,892,'[C] Commentary >',22,MAGENTA)
    s.visible_commentary_lines=2
    keep(s,'06-watched')

    s=Sheet(7,'HALF-TIME / HOLLAND 1 - 1 BELGIUM',active='Match',focus=True)
    s.card(20,108,'NL08',690,h=640,context='OFF / XI / ELIGIBLE',snapshot='halftime_profiles')
    s.card(730,108,'NL14',690,h=640,context='ON / BENCH / READY',snapshot='halftime_profiles')
    s.text(20,790,'Vermeer 18′ / Laurent 42′ / Friendly: unlimited changes',25,YELLOW)
    s.button(20,818,'Confirm Bos > Jansen',440)
    s.button(480,818,'Resume second half',400)
    s.button(900,818,'Squad / Bench >',340)
    s.footer('Enter: confirm exchange / Resume: play second half / Esc: cancel changes')
    keep(s,'07-half-time')

    s=Sheet(8,'FULL TIME / HOLLAND 2 - 1 BELGIUM',active='Match')
    s.text(178,203,'FRIENDLY / HALF TIME 1 : 1',26,GOLD,True)
    s.box(178,235,346,498,CYAN,'HOLLAND SCORERS')
    s.lines(196,310,['D Vermeer    18′','N Smit       68′'],25,55,fill=YELLOW)
    s.box(542,235,512,498,RED,'STATISTICS / HOL : BEL')
    stats=[('Corners','4 : 3'),('Free kicks','8 : 10'),('Penalties','0 : 0'),('Shots','12 : 9'),('On target','6 : 5'),('Saves','4 : 4'),('Fouls','8 : 8'),('Yellow cards','0 : 0'),('Red cards','0 : 0')]
    for i,(label,value) in enumerate(stats):
        s.text(560,290+i*34,label,24,MAGENTA)
        s.text(855,290+i*34,value,24,GREEN)
    s.text(560,629,'Possession  [ ? : ? ]',22,MAGENTA)
    s.text(560,662,'Territory   [ ? : ? ]',22,MAGENTA)
    s.text(560,705,'Meaning unverified',22,GREY)
    s.box(1072,235,350,498,CYAN,'BELGIUM SCORERS')
    s.text(1090,310,'L Laurent  42′',25,YELLOW)
    s.text(178,781,'MAN OF THE MATCH: '+P[D['man_of_the_match']]['name'],30,YELLOW,True)
    s.button(178,817,'Continue',230,selected=True)
    s.button(426,817,'Round results',280)
    s.button(724,817,'Summary',220)
    s.footer('Comparison bars shown when verified / Bos > Jansen at half-time')
    keep(s,'08-result')

    s=Sheet(9,'NEXT: EIRE / QUALIFYING')
    s.box(178,174,570,275,CYAN,'LAST MATCH')
    s.text(196,253,'HOLLAND 2 - 1 BELGIUM',32,YELLOW,True)
    s.lines(196,306,['Vermeer 18′ / Smit 68′','Belgium: Laurent 42′','Half-time 1-1 / Bos > Jansen'],24,46)
    s.box(770,174,652,405,CYAN,'GROUP F / QUALIFYING')
    s.text(788,244,'COUNTRY       P W D L F A T',24,CYAN)
    s.lines(788,298,['Holland       0 0 0 0 0 0 0','Eire          0 0 0 0 0 0 0','Denmark       0 0 0 0 0 0 0','Luxembourg    0 0 0 0 0 0 0'],24,57,fill=YELLOW)
    s.box(178,472,570,300,RED,'YOUR TEAM')
    s.lines(196,540,['Noor remains in the squad.','de Wit remains in the pool.','Jansen came on for Bos.','Review the next XI, then save.'],24,46,fill=GREEN)
    s.lines(790,635,['Friendly: no qualifying points.','Next fixture: Holland v Eire.','Save > close > Resume this career.'],24,45)
    s.button(178,817,'Prepare Eire',300,selected=True)
    s.button(500,817,'Save career',280)
    s.button(802,817,'History',230)
    s.footer('Same country / Same saved career / Competitive Watch remains unavailable')
    keep(s,'09-continue')

    s=Sheet(10,'HOLLAND / NATIONAL RECORDS / AFTER WORLD CUP 2030',active='History')
    s.box(178,174,845,234,GOLD,'STREAKS / NOW-TOP')
    s.text(196,234,'STATISTIC',23,CYAN,True)
    for xx,label in [(726,'HOME'),(820,'AWAY'),(914,'ALL')]: s.text(xx,234,label,23,CYAN,True)
    labels=[('Consecutive wins','W'),('Consecutive defeats','L'),('Games without a win','notW'),('Games without defeat','notL')]
    for i,(label,kind) in enumerate(labels):
        values=[streak(kind,venue) for venue in ('Home','Away',None)]
        s.text(196,276+i*36,label,23,CYAN)
        for xx,(now,top) in zip((726,820,914),values): s.text(xx,276+i*36,f'{now}-{top}',23,YELLOW)
    s.box(1041,174,381,234,GOLD,'SUCCESSES')
    s.lines(1059,241,['       1st 2nd 3rd 4th','WC      0   0   0   0','CH      0   0   0   0'],23,49,fill=YELLOW)
    s.box(178,431,600,278,CYAN,'RESULTS / YEAR')
    s.lines(196,494,['YEAR  CUP W D L  F A BEST PLACE','2030  WC  6 2 3 16 9 Last 16','2032  CH  - - -  - - Not started'],22,49,fill=YELLOW)
    s.text(196,665,'2030 includes Belgium friendly',21,GREY)
    s.box(796,431,312,278,RED,'2030 SCORERS')
    s.lines(814,491,[f'{name:10} {n}' for name,n in D['career_scorers']],21,41,fill=YELLOW)
    s.box(1126,431,296,278,RED,'TOP CAPS')
    s.lines(1144,491,['L de Boer   82','S Bakker    65','R van Dalen 59'],21,48,fill=GREEN)
    s.box(178,731,1244,128,GOLD,'RECORDS / WIN                     DEFEAT')
    s.lines(196,785,['HOME     4-0 Luxembourg          No home defeat','AWAY     3-0 Luxembourg          0-1 Eire','NEUTRAL  1-0 Norway              0-3 Germany'],21,29,fill=CYAN)
    s.footer('2032 cycle / [Campaign 2030 >] [Bulletin >] [Squad update >] [Return]')
    keep(s,'10-career')

    keep(team_sheet(11,focus=True,small=True),'11-small-window')

    s=Sheet(12,'CLEAR REFUSALS / RECOVERABLE ERRORS',active='Save')
    states=[('LOAD FAILED / HOLLAND','Could not open Holland-before-Belgium.sav','Your current career is still open.','[Retry] [Choose another save] [Cancel]'),
            ('STARTING WATCH / BELGIUM','Holland v Belgium / Friendly / Normal','Starting match...','[Cancel match]'),
            ('WATCH UNAVAILABLE / EIRE','Holland v Eire / World qualifying','Watch is available for scheduled friendlies.','[Start Quick] [Return to preparation]')]
    for i,(title,line1,line2,actions) in enumerate(states):
        y=174+i*211
        s.box(178,y,1244,185,RED,title)
        s.text(196,y+66,line1,26,WHITE)
        s.text(196,y+108,line2,24,YELLOW)
        s.text(196,y+154,actions,25,CYAN,True)
    s.footer('Esc: cancel / F1: Help')
    keep(s,'12-unavailable-errors')

    s=Sheet(13,'KNOCKOUT DECISIONS / CONDITIONAL',active='Match')
    s.box(178,174,586,620,RED,'EXTRA TIME / IF REQUIRED')
    s.text(196,245,'NORMAL TIME 1 : 1',30,YELLOW,True)
    s.lines(196,304,['90′   Holland 1 - 1 Germany','105′  Holland 1 - 1 Germany','Captain: L de Boer','On: J Jansen / Off: P Bos','[Team] [Tactics] [Resume]'],23,56)
    s.button(196,671,'Squad / full bars >',540)
    s.box(786,174,636,620,CYAN,'STILL LEVEL / ORDER TAKERS')
    s.text(804,245,'AFTER EXTRA TIME 1 : 1',29,YELLOW,True)
    for i,k in enumerate(second_xi):
        xx=804+(i//6)*305; yy=315+(i%6)*48
        s.text(xx,yy,f'{i+1:02} '+P[k]['name'],23,ROLE_COLORS[P[k]['role']],True)
    s.button(804,671,'Undo',170)
    s.button(992,671,'Confirm order',400)
    s.text(804,761,'Arrows: reorder / Enter: confirm',23,MAGENTA)
    s.footer('Hypothetical later knockout / Esc: return / F1: Help')
    keep(s,'13-conditional')

    keep(team_sheet(14,focus=True),'14-team-focus')

    s=Sheet(15,'HOLLAND 1 - 0 BELGIUM / 38′',active='Match')
    # [designed] The open drawers use space only on explicit request. The closed
    # state is sheet06, with the same minute, score and event chronology.
    pitch(s,178,174,830,650)
    s.box(1024,174,398,650,CYAN,'COMMENTARY / [C] HIDE')
    s.lines(1042,243,['18′ GOAL: Vermeer','    Holland 1-0','31′ Keeper collects','35′ Belgium attacks','38′ Play continues'],23,34,fill=CYAN)
    s.text(1042,785,'Holland: gold',20,GOLD)
    s.text(1042,813,'Belgium: white',20,WHITE)
    s.footer('C: close commentary / F11: retract bars / Both return space to the pitch')
    keep(s,'15-watched-drawers')
    s=Sheet(16,'TEAM TACTICS / HOLLAND v BELGIUM',active='Team')
    s.box(178,174,560,618,GOLD,'HOLLAND / XI 11 / 4-4-2')
    s.lines(196,237,['Manager: Alex / Captain: L de Boer','World 14 / Europe 3','Strips: Gold / White (schematic)'],22,42,fill=YELLOW)
    s.text(196,382,'TEAM SKILLS / ORIGINAL SCALE',23,RED,True)
    for i,label in enumerate(['Keeper','Defence','Midfield','Attack']):
        yy=427+i*39
        s.text(196,yy,label,23,GOLD)
        s.text(360,yy,'[ ? ? ? ? ? ? ? ]',23,GREY)
    s.text(196,603,'Aggregate encoding unverified',22,GREY)
    s.lines(196,654,['Performance K/D/M/A: No performance',f"XI mean caps {sum(P[k]['caps'] for k in D['xi'])//11} / age {sum(P[k]['age'] for k in D['xi'])//11}",'Hardness / Fitness / Energy / Morale','Aggregate display: unverified'],21,33,fill=GREEN)
    s.box(756,174,666,618,RED,'TEAM DEFAULTS')
    tactics=[('Defence system','Full pitch'),('Protection','Stand ground'),('Offside','Offside trap'),('Positioning','Push forward'),('Possession','Keep ball'),('Passing','Short passes'),('Tackling','Avoid injury'),('Marking','Man to man')]
    for i,(label,value) in enumerate(tactics):
        s.text(776,247+i*59,label,24,GOLD)
        s.text(1060,247+i*59,value,24,GREEN)
    s.button(178,817,'Formation / roles >',350)
    s.button(548,817,'Confirm plan',290,selected=True)
    s.button(858,817,'Discard / Team',320)
    s.footer('Enter: change selected tactic / Personal instructions keep their explicit source')
    keep(s,'16-team-tactics')

    s=Sheet(17,'SELECT YOUR TEAM',active='Team',focus=True,small=True)
    s.box(20,103,860,374,CYAN,'SQUAD / 20 / XI 11 / BENCH 9')
    for i,k in enumerate(squad[:11]):
        yy=160+i*28
        s.text(38,yy,f'{i+1:02}  '+P[k]['name'],24,ROLE_COLORS[P[k]['role']],True)
        s.text(370,yy,P[k]['role']+(' C' if k==D['captain'] else ''),24,ROLE_COLORS[P[k]['role']])
        s.text(580,yy,'XI / Ready',24,GREEN)
    s.rect(855,142,8,320,EMPTY)
    s.rect(855,142,8,176,GREY)
    s.text(20,510,'1-11 of 20 / Scroll: bench 12-20 / Selected: J Jansen',21,YELLOW)
    s.button(20,534,'Pool / Compare',270)
    s.button(310,534,'Attribute table',280)
    s.button(610,534,'Team tactics',270)
    s.button(20,586,'Player Jansen >',300)
    s.button(340,586,'Confirm team',260)
    s.button(620,586,'Discard',260)
    keep(s,'17-small-roster')

    s=Sheet(18,'2032 / RETIREMENT AND REPLACEMENT',focus=True,active='Team')
    s.card(20,108,'NL08',690,h=640,context='RETIRED / NOT SELECTABLE',snapshot='later_profiles')
    s.card(730,108,'NL22',690,h=640,context='IN / POOL / READY',snapshot='later_profiles')
    s.text(20,790,'P Bos: age 31 > 33 / 46 > 51 caps / National place now vacant',24,YELLOW)
    s.button(20,818,'Review van Rijn >',370)
    s.button(410,818,'Add van Rijn',300,selected=True)
    s.button(730,818,'Browse pool',300)
    s.footer('2032 European cycle / Alex / [Bulletin >] [Country >] / Same saved country')
    keep(s,'18-later-squad')

    s=Sheet(19,'WORLD CUP 2030 / COMPLETED CAMPAIGN',active='Fixtures')
    s.box(178,174,600,287,CYAN,'FINAL QUALIFYING / GROUP F')
    s.lines(196,237,['COUNTRY     P W D L  F  A  T','Holland     6 4 1 1 12  2  9','Denmark     6 3 2 1  9  4  8','Eire        6 3 1 2  5  5  7','Luxembourg  6 0 0 6  0 15  0'],22,43,fill=YELLOW)
    s.box(796,174,626,287,GOLD,'HOLLAND / QUALIFYING RESULTS')
    s.lines(814,235,['H  Eire          2-0','A  Denmark       1-1','H  Luxembourg    4-0','A  Eire          0-1','H  Denmark       2-0','A  Luxembourg    3-0'],23,36,fill=CYAN)
    s.box(178,485,600,308,RED,'WORLD FINALS / HOLLAND ROUTE')
    s.lines(196,548,['GROUP   Norway    1-0','GROUP   Chile     1-1','GROUP   Italy     0-2','LAST 16 Germany   0-3','        Holland eliminated'],24,48,fill=YELLOW)
    s.box(796,485,626,308,CYAN,'NATIONAL BULLETIN / 2032')
    s.lines(814,547,['WORLD CUP: OUT IN THE LAST 16','Germany 3 - 0 Holland','P Bos retires / age 33 / caps 51','S van Rijn enters the national pool','Next: European qualifying'],23,47,fill=GREEN)
    s.button(178,817,'Finals bracket >',320)
    s.button(518,817,'Records >',270)
    s.button(809,817,'Continue 2032 >',360,selected=True)
    s.footer('Completed 2030 campaign / Next cycle: Holland, manager Alex / [Squad update >]')
    keep(s,'19-campaign')
    return exports


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    target=ROOT/'screens'; target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='goal2-vision-266-') as tmp:
        out=Path(tmp); exports=draw(out)
        for svg,_,_ in exports:
            env={**os.environ,'INKSCAPE_PROFILE_DIR':str(out/'inkscape-profile')}
            subprocess.run(['inkscape',str(svg),'--export-type=png','--export-filename='+str(svg.with_suffix('.png'))],check=True,capture_output=True,env=env)
            for suffix in ['.svg','.png']:
                source=svg.with_suffix(suffix); dest=target/source.name
                if args.check:
                    if not dest.exists() or dest.read_bytes()!=source.read_bytes():
                        raise SystemExit('FAIL missing/stale export: '+str(dest))
                else: dest.write_bytes(source.read_bytes())
        if args.check:
            assert {p.name for p in target.iterdir()}=={p.with_suffix(s).name for p,_,_ in exports for s in ['.svg','.png']}
        print(f'PASS coherent story; {len(exports)} sheets; {sum(n for _,n,_ in exports)} measured text bounds; {sum(n for _,_,n in exports)} attribute bars; actual field >=82%, commentary 2 lines; '+('exports identical' if args.check else 'exports written'))


if __name__=='__main__': main()
