"""[designed: #266] Offline static illustration authoring; never runs the game.

Run without arguments to retain SVG/PNG exports; --check regenerates in a
temporary directory and verifies the committed exports. Requires Pillow and
Inkscape only in the author's environment, not in the application.
"""
from pathlib import Path
import argparse
import html
import json
import os
import subprocess
import tempfile
from PIL import ImageFont

ROOT = Path(__file__).resolve().parent
D = json.loads((ROOT / 'scenario.json').read_text())
P = {p['key']: p for p in D['players']}
INK, GREEN, PAPER, MUTED = '#152d34', '#006958', '#f3f1e9', '#52656a'
SKILLS = ['Keeping', 'Kicking', 'Tackling', 'Heading', 'Marking', 'Passing',
          'Crossing', 'Feinting', 'Control', 'Dribbling', 'Shooting', 'Penalties']
FONT_ROOT = Path('/usr/share/fonts/truetype/dejavu')
FONTS = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in FONTS:
        FONTS[key] = ImageFont.truetype(str(FONT_ROOT / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')), size)
    return FONTS[key]


class Sheet:
    def __init__(self, number, title, subtitle, small=False, active='Country desk', dark=False):
        self.w, self.h = (900, 640) if small else (1440, 900)
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}">',
                      f'<title>{html.escape(title)}</title><desc>Designed finished-target illustration. Fictional data. Not current build or engine output.</desc>']
        self.bounds = []
        self.rect(0, 0, self.w, self.h, PAPER)
        self.rect(0, 0, self.w, 78 if not small else 65, INK)
        self.text(22, 29, 'GOAL2  /  COUNTRY MANAGER', 14, '#e7f1e7', True)
        self.text(22, 59 if not small else 52, 'HOLLAND  •  Alex  •  2030', 17, 'white', True)
        self.text(650 if not small else 465, 31, f'{number:02}  FINISHED TARGET', 15, '#f1ce71', True)
        self.text(650 if not small else 465, 56 if not small else 52, 'Static illustration • fictional data • not current build', 12, 'white')
        self.small = small
        self.number = number
        if small:
            self.text(20, 91, 'Country desk   |   Team   |   Competition   |   Match centre   |   Archive   |   Game', 14, INK)
            self.text(20, 123, title, 22, INK, True)
            self.text(20, 148, subtitle, 13)
        else:
            self.rect(0, 78, 170, 822, INK)
            for i, item in enumerate(['Country desk', 'Team', 'Competition', 'Match centre', 'Archive', 'Game / Save']):
                y = 121 + i * 54
                if item == active:
                    self.rect(12, y - 25, 146, 40, GREEN, 5)
                self.text(22, y, item, 15, 'white', item == active)
            self.text(22, 819, 'Help  /  F1', 14, 'white')
            self.text(194, 123, title, 28, INK, True)
            self.text(194, 153, subtitle, 15)
        self.rect(0 if small else 170, self.h - 37, self.w if small else self.w - 170, 37, '#e2e8e1')
        self.text(16 if small else 194, self.h - 14, 'DESIGNED • No game controls are active. Target review is not implementation approval.', 11)

    def rect(self, x, y, w, h, fill='white', radius=0, stroke=None):
        assert x >= 0 and y >= 0 and x+w <= self.w and y+h <= self.h, (x,y,w,h)
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}"'+(f' stroke="{stroke}"' if stroke else '')+'/>')

    def text(self, x, y, value, size=15, fill=MUTED, bold=False):
        value = str(value)
        f = font(size, bold)
        box = f.getbbox(value)
        width = f.getlength(value)
        assert x >= 0 and x+width <= self.w-8 and y-size >= 0 and y+box[3]-size <= self.h, (value,x,y,width)
        self.bounds.append((value,x,y,width,size))
        self.parts.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans" font-size="{size}" font-weight="{700 if bold else 400}" fill="{fill}">{html.escape(value)}</text>')

    def lines(self, x, y, values, size=15, step=27, **kw):
        for i,v in enumerate(values): self.text(x,y+i*step,v,size,**kw)

    def panel(self, x, y, w, h, title):
        self.rect(x,y,w,h,'white',7,'#d1dbd5')
        self.text(x+18,y+30,title,18,INK,True)

    def button(self, x, y, label, w=210, disabled=False):
        self.rect(x,y,w,40,'#e2e6e4' if disabled else GREEN,5)
        self.text(x+13,y+26,label,14,MUTED if disabled else 'white',True)
        assert font(14,True).getlength(label) < w-20, label

    def card(self, x, y, key, w=360, compact=False, context='Squad • bench • ready'):
        p=P[key]
        h=411 if compact else 586
        self.panel(x,y,w,h,p['name']+'  /  '+p['role'])
        self.lines(x+16,y+58,[f"{p['age']} years • {p['caps']} caps • {p['goals']} goals • {p['height']}",
                                  f"{p['foot']} foot • national {p['national_position']} / club {p['club_position']}",
                                  context, 'Cards: '+p['cards'], 'Performance: '+p['performance']],12,20)
        self.text(x+16,y+164,'ILLUSTRATIVE SOURCE UNITS • NOT %',10,MUTED,True)
        start=y+188
        for i,(name,val) in enumerate(zip(SKILLS,p['skills'])):
            col=i//6; row=i%6; xx=x+16+col*((w-32)/2)
            yy=start+row*(21 if compact else 29)
            self.text(xx,yy,name,12 if compact else 14)
            self.text(xx+(w-32)/2-31,yy,val,12 if compact else 14,INK,True)
        base=start+6*(21 if compact else 29)+7
        chars=[('Hardness',p['hardness']),('Fitness',p['fitness']),('Energy',p['energy']),('Morale',p['morale']),('Leadership',p['leadership'])]
        if compact:
            self.lines(x+16,base,['  •  '.join(f'{k} {v}' for k,v in chars[:3]), '  •  '.join(f'{k} {v}' for k,v in chars[3:])],11,21)
            self.lines(x+16,base+48,['Instructions: Team defaults (five categories)', 'Open personal / team instructions'],11,20)
        else:
            for i,(name,val) in enumerate(chars):
                self.text(x+16,base+i*25,name,13)
                self.text(x+w-45,base+i*25,val,13,INK,True)
            self.lines(x+16,base+143,['Position / Possession / Passing / Tackling', 'Team defaults • Mark: team default', 'Personal / Team source remains explicit'],11,20)

    def roster(self, x, y, keys, xi, row=25):
        self.text(x,y,'XI   PLAYER',12,MUTED,True)
        for offset,label in [(255,'POS'),(295,'ABIL'),(339,'ENG'),(381,'CONF'),(434,'READY')]:
            self.text(x+offset,y,label,10,MUTED,True)
        for i,k in enumerate(keys):
            yy=y+30+i*row
            if k=='NL14': self.rect(x-3,yy-18,492,row,'#d9eee3',0,GREEN)
            elif i%2==0: self.rect(x-3,yy-18,492,row,'#f1f5f0')
            self.text(x,yy,'✓' if k in xi else '—',13,GREEN,True)
            self.text(x+29,yy,P[k]['name']+('  C' if k==D['captain'] else ''),13,INK,k==D['captain'])
            for offset,value in [(255,P[k]['role']),(295,210),(339,P[k]['energy']),(381,P[k]['morale']),(434,'Yes')]:
                self.text(x+offset,yy,value,11)

    def note(self, lines):
        self.lines(194,790,lines,13,23)

    def save(self, directory, slug):
        # [designed] The complete-card illustrations must actually retain every
        # category; image-byte regeneration alone cannot establish that contract.
        count = {3: 1, 4: 2, 7: 2, 11: 1}.get(self.number, 0)
        if count:
            texts = [b[0] for b in self.bounds]
            for category in SKILLS + ['Hardness', 'Fitness', 'Energy', 'Morale', 'Leadership']:
                assert sum(category in value for value in texts) >= count, (slug, category)
        if self.number == 3:
            assert all(any(P[key]['name'] in b[0] for b in self.bounds) for key in D['initial_squad'])
        path=directory/(slug+'.svg')
        path.write_text('\n'.join(self.parts+['</svg>'])+'\n')
        return path, len(self.bounds)


def validate_scenario():
    assert len(P)==21 and len(D['initial_squad'])==20 and len(set(D['initial_squad']))==20
    assert len(D['xi'])==11 and set(D['xi'])<=set(D['initial_squad']) and D['captain'] in D['xi']
    # [designed] The authored 4–4–2 must match the displayed starting roles.
    roles=[P[k]['role'] for k in D['xi']]
    assert roles.count('GK')==1 and sum(r in ('LB','RB','CB','SW') for r in roles)==4
    assert roles.count('MF')==4 and roles.count('FW')==2
    ex=D['pool_exchange']; assert ex['out'] not in D['xi'] and ex['in'] not in D['initial_squad']
    squad=[ex['in'] if k==ex['out'] else k for k in D['initial_squad']]
    sub=D['halftime_exchange']; assert sub['out'] in D['xi'] and sub['in'] in squad and sub['in'] not in D['xi']
    xi=[sub['in'] if k==sub['out'] else k for k in D['xi']]
    for p in P.values(): assert len(p['skills'])==12 and all(0<=v<=25 for v in p['skills'])
    def score(t): return [sum(e['side']==s and e['minute']<=t for e in D['events']) for s in ['Holland','Belgium']]
    assert score(38)==[1,0] and score(45)==D['halftime_score'] and score(90)==D['final_score']
    assert all(e.get('player') in (D['xi'] if e['minute']<=45 else xi) for e in D['events'] if e['side']=='Holland')
    assert len(D['belgium_xi'])==11
    # [designed] This renderer draws a fixed story, not arbitrary simulation data.
    # Reject drift between the explicit prose/image chronology and the scenario.
    assert [(e['minute'],e['side'],P[e['player']]['name'] if 'player' in e else e['name']) for e in D['events']] == [(18,'Holland','D Vermeer'),(42,'Belgium','L Laurent'),(68,'Holland','N Smit')]
    assert (P[ex['out']]['name'],P[ex['in']]['name']) == ('C de Wit','R Noor')
    assert (P[sub['out']]['name'],P[sub['in']]['name']) == ('P Bos','J Jansen')
    assert P[D['captain']]['name']=='L de Boer' and D['next_opponent']=='Eire'
    return squad,xi


def draw(directory):
    squad,second_xi=validate_scenario()
    exports=[]
    def keep(s,slug): exports.append(s.save(directory,slug))
    s=Sheet(1,'Return to your country','Start / Resume • the same career remains yours',active='Game / Save')
    s.panel(194,185,700,481,'Your saved career')
    s.text(222,268,'HOLLAND',42,INK,True)
    s.lines(222,314,['Alex • 2030 World qualifying campaign', 'Next fixture: Holland v Belgium • scheduled friendly', 'Next competitive opponent: Eire • qualifying', 'Last committed checkpoint: before Belgium', 'One manager • confirmed team • no match pending'],18,43)
    s.button(222,584,'Resume Holland',250)
    s.panel(916,185,498,481,'Start something new')
    s.lines(938,249,['New career → choose country → inspect players', 'Review identity, manager count and challenge.', 'Starting replaces no save without your choice.', '', 'Country profiles and editable identities need', 'their supported data and persistence paths.'],16,36)
    s.button(938,545,'Choose country',250)
    s.button(938,599,'Open another save',250)
    s.note(['A new career has its own explicit review/start step; Resume keeps the saved country and checkpoint.', 'Complete local-manager setup belongs to the target; first delivery can clearly offer one manager only.'])
    keep(s,'01-start-resume')
    s=Sheet(2,'The country desk','World qualifying campaign • before the Belgium friendly')
    s.panel(194,185,754,256,'Next challenge  /  scheduled friendly')
    s.text(216,269,'Holland v Belgium',36,INK,True)
    s.lines(216,311,['At home • Holland rank 14 / Belgium rank 8 (illustrative)', 'Friendly: no qualification points at stake.', 'Then Eire in qualifying • review the team before kickoff'],17,32)
    s.button(216,383,'Prepare Belgium',230)
    s.panel(970,185,444,256,'Your campaign')
    s.lines(992,249,['Qualifying • Group F • opening table', 'Holland / Eire / Denmark / Luxembourg', 'All played 0 • no results yet', 'Standings and group fixtures together'],15,34)
    s.button(992,377,'Open competition',230)
    s.panel(194,463,754,280,'Your people')
    s.lines(216,525,['Twenty in the squad • eleven starters / nine bench', 'Captain: L de Boer • current plan: 4–4–2', 'Review C de Wit against reserve R Noor.', 'Readiness and availability stay beside each decision.'],17,38)
    s.button(216,675,'Review Team',230)
    s.panel(970,463,444,280,'National story')
    s.lines(992,525,['Latest news and career records live here.', 'This save has no completed match yet.', 'Future records are not fabricated.', '', 'Open Country profile / Archive'],16,36)
    s.note(['The next action and national context come first. Original country/profile/history categories remain discoverable.', 'Rankings, generated bulletin and complete records are finished-target data; current main does not supply all of them.'])
    keep(s,'02-country-desk')
    s=Sheet(3,'Make an informed team choice','Same pre-match squad • select a row, inspect the complete card, review your plan',active='Team')
    s.panel(194,185,535,586,'Squad 20  /  XI 11  /  Bench 9')
    s.roster(211,247,D['initial_squad'],D['xi'],23)
    s.card(749,185,'NL14',360,context='J Jansen • bench • ready')
    s.panel(1129,185,285,586,'Your plan')
    s.lines(1147,246,['Formation: 4–4–2', 'Captain: L de Boer', 'Team instructions', 'Player instructions', 'National pool / Compare', '', 'No unconfirmed changes', 'Selected: J Jansen', '', 'Show all attributes', 'Squad: 38 columns', 'Pool: 37 columns', 'Contained horizontal scroll'],14,34)
    s.note(['All twenty names stay in Team; seven compact columns are retained. Complete details never become an aggregate rating.', 'Unknown performance meaning is not guessed. Role/marking edits depend on supported state and context.'])
    keep(s,'03-team')
    s=Sheet(4,'Compare before replacing a squad place','Before kickoff • one bench place changes • original eligibility rules still apply',active='Team')
    s.panel(194,185,340,586,'National pool  /  reserves 80')
    s.lines(212,251,['Search / position filter', 'Rows 1–7 of 80 • contained scroll', 'R Noor          FW     Ready', 'V Groen         FW     Ready', 'W Hermans       MF     Ready', 'X van Vliet     CB     Ready', 'Y Jonker        GK     Ready', 'Z Maas          MF     Ready', 'A Bosman        FW     Ready', '', 'Pinned: C de Wit → R Noor', 'Neither player is in the XI.', 'Review → Confirm or Cancel'],14,34)
    s.rect(517,315,5,230,'#e2e8e1',2)
    s.rect(517,315,5,28,GREEN,2)
    s.card(554,185,'NL20',420,context='Outgoing • squad bench • ready')
    s.card(994,185,'NL21',420,context='Incoming • national pool • ready')
    s.button(554,788,'Confirm de Wit → Noor',290)
    s.text(870,814,'After this step: Noor on bench; de Wit in pool.',14)
    keep(s,'04-pool')
    s=Sheet(5,'Prepare both sides, then choose how to play','Holland v Belgium • scheduled friendly • Noor has replaced de Wit on the bench',active='Match centre')
    s.panel(194,185,378,564,'Holland  /  4–4–2')
    for i,k in enumerate(D['xi']): s.text(214,251+i*30,P[k]['name']+('  C' if k==D['captain'] else '')+'  /  '+P[k]['role'],16,INK)
    s.text(214,620,'XI11 • Bench9 • all ready',14)
    s.button(214,678,'Review Team',220)
    s.panel(592,185,378,564,'Belgium  /  4–4–2')
    for i,name in enumerate(D['belgium_xi']): s.text(612,251+i*30,name,16,INK)
    s.button(612,678,'Inspect opponent',220)
    s.panel(990,185,424,564,'Match delivery')
    s.lines(1010,249,['Quick result', 'Resolve without watched pitch playback.', 'Supported decisions may still pause play.', '', 'Watch match', 'Follow the pitch and commentary.', 'Current friendly Watch is view-only.', 'Target interventions need proven support.', '', 'Playback: Slow  |  Normal ✓  |  Fast', 'Choose now; frozen during this match.', 'Quick / Watch can produce different results.'],14,29)
    s.button(1010,635,'Start Watch',250)
    s.button(1010,687,'Start Quick',250)
    s.note(['The story chooses Watch at Normal. No match starts while team changes await confirmation.', 'The next Eire qualifier is a different fixture: competitive Quick exists; competitive Watch remains a capability gap.'])
    keep(s,'05-preparation')
    s=Sheet(6,'HOLLAND   1 — 0   BELGIUM     38′','First half • Vermeer 18′ • this is one illustrative supplied frame, not simulated motion',active='Match centre')
    s.rect(194,185,780,520,GREEN,7)
    s.rect(222,213,724,464,'#227e69',0,'#c8e0d3')
    s.parts.append('<path d="M584 213 V677 M222 325 H310 V565 H222 M946 325 H858 V565 H946" fill="none" stroke="#c8e0d3" stroke-width="2"/><circle cx="584" cy="445" r="63" fill="none" stroke="#c8e0d3" stroke-width="2"/>')
    for team in range(2):
        for i in range(11):
            x=267+(i%4)*157+(40 if team else 0); y=256+(i//4)*145+(46 if team else 0)
            s.parts.append(f'<circle cx="{x}" cy="{y}" r="15" fill="'+('#f5cc69' if team==0 else '#f0f2ed')+'"/>')
            s.text(x-7,y+5,i+1,11,INK,True)
    s.parts.append('<circle cx="620" cy="425" r="7" fill="white" stroke="#152d34" stroke-width="3"/>')
    s.text(214,739,'● Holland   ○ Belgium   • Ball / supplied positions only',16,INK)
    s.panel(994,185,420,520,'Commentary  /  Follow live')
    s.lines(1014,252,['38′  Play continues', '35′  Belgium builds an attack', '31′  Keeper collects', '18′  Goal — D Vermeer', '       Holland leads 1–0', '', 'Score, clock and event log agree.', 'No invented timer or interpolation.', '', 'Speed: Normal • chosen before kickoff'],16,35)
    s.button(194,782,'Manage — unavailable now',300,True)
    s.text(515,807,'No supported decision at this moment. Commentary remains readable.',14)
    keep(s,'06-watched')
    s=Sheet(7,'Half-time   /   Holland 1 — 1 Belgium','Vermeer 18′ • Laurent 42′ • finished-target supported decision, not current watched capability',active='Match centre')
    s.card(194,185,'NL08',390,context='Off • starter • eligible')
    s.card(604,185,'NL14',390,context='On • bench • ready')
    s.panel(1014,185,400,586,'Review the change')
    s.lines(1034,249,['Off: P Bos • midfield', 'On: J Jansen • midfield', 'XI remains eleven.', 'Captain remains L de Boer.', '', 'Friendly policy: unlimited changes.', 'Actual eligibility/refusals still apply.', '', 'Confirm substitution, then Resume.', 'Cancel keeps the committed XI.', 'No real-time touchline commands.'],15,35)
    s.text(1034,638,'Open squad20 / XI11 / Bench9',15,GREEN,True)
    s.button(1034,664,'Confirm Bos → Jansen',350)
    s.button(194,790,'Resume second half',290)
    s.text(508,815,'This story confirms the change. Current friendly Watch remains view-only.',14)
    keep(s,'07-half-time')
    s=Sheet(8,'Holland  2 — 1  Belgium','Full time • scheduled friendly • half-time1–1 • no extra time or shoot-out',active='Match centre')
    s.panel(194,185,580,535,'What happened')
    s.lines(216,251,['Holland', '18′  D Vermeer', '68′  N Smit', '', 'Belgium', '42′  L Laurent', '', 'Half-time: 1–1  /  Full time: 2–1', 'Half-time change: Bos → Jansen', 'Man of the match: Not recorded'],18,37)
    s.panel(794,185,620,535,'Statistics  /  Holland : Belgium')
    stats=['Corners                    4 : 3','Free kicks                  8 : 10','Penalties                    0 : 0','Shots                      12 : 9','On target                    6 : 5','Saves                        4 : 4','Fouls                        8 : 8','Yellow cards                 0 : 0','Red cards                    0 : 0','Possession / Territory      Not recorded']
    s.lines(816,250,stats,17,38)
    s.button(194,760,'Continue to country desk',330)
    s.button(546,760,'Round results',240)
    s.button(808,760,'Retained summary',260)
    s.text(194,836,'A genuine zero remains 0. Missing data stays Not recorded. New summary capture/replay needs durable support.',13)
    keep(s,'08-result')
    s=Sheet(9,'Your next challenge is Eire','After the Belgium friendly • keep the national story and prepare the qualifier')
    s.panel(194,185,754,278,'Last result  /  Holland 2–1 Belgium')
    s.lines(216,254,['Vermeer18′, Smit68′ / Laurent42′', 'Half-time1–1 • Bos→Jansen at the interval', 'No qualification points awarded for this friendly.', 'Your squad still includes Noor; de Wit remains in the pool.'],17,38)
    s.button(216,395,'Prepare Eire qualifier',290)
    s.panel(970,185,444,278,'Group F  /  qualifying')
    s.lines(992,251,['Country         P W D L F A T', 'Holland         0 0 0 0 0 0 0', 'Eire            0 0 0 0 0 0 0', 'Denmark         0 0 0 0 0 0 0', 'Luxembourg      0 0 0 0 0 0 0'],15,34)
    s.panel(194,485,1220,258,'Save this career, then return')
    s.lines(216,547,['Confirm the next team before saving: match effects and final XI are authoritative, not copied from the pre-match picture.', 'Save → success → close → Resume Holland at the same committed post-Belgium checkpoint.', 'Fixtures, country profile, rankings and Archive remain available routes; the next opponent is Eire.', 'The first delivery may stop at an explained unsupported future-stage boundary; that is not a finished career.'],17,37)
    s.note(['The friendly did not advance the qualifying table. Later competitive results must use the actual accepted standings rules.', 'Next: prepare again, play the qualifier, follow the campaign, then revisit the people and records.'])
    keep(s,'09-continue')
    s=Sheet(10,'A country over successive campaigns','Longer-career target • later milestones, not states immediately after the Belgium friendly',active='Archive')
    for x,title,lines in [(194,'2030  /  pursue qualification',['Review the group and remaining fixtures.', 'Earn finals or understand elimination.', 'Blank future pairings stay unplayed.', 'Do not fabricate automatic qualification.']), (814,'After the campaign',['Keep results, scorers and country records.', 'Read supported bulletin consequences.', 'Continue after disappointment.', 'A headline alone never means dismissal.'])]:
        s.panel(x,185,600,235,title); s.lines(x+20,247,lines,17,35)
    s.panel(194,442,1220,295,'2032 and beyond  /  your country changes, your decisions continue')
    s.lines(216,506,['Ageing, retirement and national-pool replacement belong to the complete career.', 'Illustrative later record: P Bos leaves the squad; new candidate S van Rijn awaits comparison.', 'No retirement threshold, generated record or automatic promotion is inferred from that example.', 'Manager / national-team history, rankings, full profile and retained summaries tell the longer story.', 'Complete local-manager play hands off the correct country without losing shared fixture/save ownership.'],18,39)
    s.note(['These are desired outcomes over existing evidenced contracts, not newly specified progression rules or a delivery plan.', 'Full country projections, generated news, durable records/replay and local-manager capability still need their named support.'])
    keep(s,'10-career')
    s=Sheet(11,'Team  /  J Jansen','900×640 logical client • pre-kickoff after Noor exchange • same full-card data',small=True,active='Team')
    s.panel(20,167,390,411,'Squad20 • XI11 / Bench9')
    s.lines(36,222,['Rows1–8 of20   ↓ contained scrollbar', '✓ R van Dalen    GK', '✓ M Vos          RB', '✓ L de Boer C    CB', '✓ T Visser       CB', '✓ J Meijer       LB', '✓ S Bakker       MF', '✓ D Vermeer      MF', '✓ P Bos          MF', '', 'Selected: J Jansen • Noor on bench'],14,26)
    s.rect(395,242,5,225,'#e2e8e1',2); s.rect(395,242,5,90,GREEN,2)
    s.button(36,530,'Jump to bench9',170); s.button(224,530,'Confirm / Discard',170)
    s.card(430,167,'NL14',450,compact=True,context='Bench • ready • no unconfirmed changes')
    s.text(20,596,'Larger text: labelled Roster / Player card / Plan panes, with selected identity and actions retained.',12)
    keep(s,'11-small-window')
    s=Sheet(12,'Clear boundaries and recoverable errors','Three alternative states of the same Holland career • not a sequence of successful actions',active='Game / Save')
    rows=[('Load failed / Holland pre-Belgium','The selected save could not be read. Active career and prior good file remain intact.', 'Retry  /  Choose another save  /  Cancel'),('Starting Watch / Holland v Belgium','Match is starting. Team edits and saving are locked until this job finishes or cancels.', 'Cancel → confirmed pre-match checkpoint; never publish a partial result'),('Watch unavailable / next Eire qualifier','Competitive Watch is not supported here. Your fixture and confirmed team remain selected.', 'Play supported Quick  /  Return to preparation')]
    for i,(title,line,action) in enumerate(rows):
        y=185+i*190; s.panel(194,y,1220,170,title); s.text(216,y+77,line,17); s.text(216,y+124,action,16,GREEN,True)
    s.note(['Save failure likewise keeps the prior good save and active career: Retry / Save elsewhere / Cancel.', 'Invalid lineup/exchange keeps the draft and names the actual refusal. No silent fallback to a new career or no-op button.'])
    keep(s,'12-unavailable-errors')
    s=Sheet(13,'Conditional phases belong to the fixture','Later knockout branch of the career • hypothetical tied match, not the Belgium friendly',active='Match centre')
    s.panel(194,185,590,522,'Branch A  /  level after normal time')
    s.lines(216,252,['Regulation: 1–1', 'Show the supplied competition phase.', 'Offer only a supported extra-time action.', '', 'At the supplied midpoint:', 'show current score, eligible team and choices;', 'Resume continues the same match.', '', 'If extra time produces a winner:', 'explain regulation and extra-time scores;', 'go to results without penalty ordering.'],17,36)
    s.panel(804,185,610,522,'Branch B  /  still level after extra time')
    s.lines(826,252,['Regulation1–1 / after extra time1–1', 'Eligible XI • complete order preview (illustrative)', 'Same example roster after Bos → Jansen'],16,30)
    for i,k in enumerate(second_xi):
        s.text(826+(i//6)*275,365+(i%6)*35,f'{i+1:02}  '+P[k]['name'],16,INK)
    s.button(826,603,'Undo',160); s.button(1004,603,'Confirm order',220)
    s.text(826,680,'Watched ordering is a capability gap today.',16)
    s.note(['Both branches preserve complete eligible-player cards and XI/bench context; they do not enable new modes or rules.', 'Competitive Quick has supported resolution output. That is not proof of interactive competitive Watch or taker ordering.'])
    keep(s,'13-conditional')
    s=Sheet(14,'Which game do you want to return to?','Same Holland v Belgium fixture, same parity requirement • three credible organizations')
    options=[(194,'A  COUNTRY DESK',GREEN,['Repeated management decisions stay close.', 'Compact tables beside complete cards.', 'Recommended. Screens02–09 show it.']), (604,'B  BROADCAST CAREER',INK,['More screen space for match spectacle.', 'Details and comparisons require drawers.', 'Greater art/motion and navigation cost.']), (1014,'C  COMMAND ROOM','#66583b',['Closest to the original menu rhythm.', 'Modern type, controls and visible keys.', 'More hopping between decisions.'])]
    for x,title,color,lines in options:
        s.rect(x,185,400,70,color,7); s.text(x+15,229,title,16,'white',True)
        s.rect(x,270,400,448,'white',7,'#d1dbd5'); s.lines(x+16,617,lines,14,33)
    s.rect(210,290,368,66,'#e3eee3',5); s.text(224,318,'Holland v Belgium  /  Prepare',16,GREEN,True)
    s.text(224,343,'Country • campaign • next action',13)
    s.rect(210,373,209,190,'#eef2ed',5); s.text(223,401,'SQUAD20  /  XI11',14,INK,True)
    s.lines(223,433,['Name       Pos     Ready','Van Dalen   GK      Yes','De Boer     CB      Yes','Jansen      MF      Yes','All rows / full comparison'],12,27)
    s.rect(431,373,147,190,'#e3eee3',5); s.lines(442,405,['PLAYER CARD','Biography','12 skills','5 characteristics','Instructions'],12,30)
    s.rect(620,290,368,273,INK,5); s.text(636,322,'HOLLAND v BELGIUM',22,'white',True)
    s.rect(636,345,336,148,GREEN,5); s.text(664,416,'MATCH / NATIONAL STORY',16,'white',True)
    s.text(636,530,'Open Team drawer  /  Open campaign drawer',12,'white')
    s.rect(1030,290,368,273,'#eeeade',5); s.text(1045,321,'Holland  /  Manager menu',18,INK,True)
    s.lines(1045,360,['1 Squad              2 Team tactics','3 Fixtures           4 Tournament','5 Country            6 History','F1 Help   /   F7 Save'],14,39)
    s.text(1045,536,'Choose → separate complete decision page',12)
    s.note(['Aesthetic direction changes navigation and reading effort; none removes complete cards or adds new football mechanics.', 'Owner selection comes before reconciling the existing plan/backlog. Toolkit choice follows the selected experience.'])
    keep(s,'14-directions')
    return exports


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    target=ROOT/'screens'; target.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='goal2-vision-266-') as tmp:
        out=Path(tmp); exports=draw(out)
        for svg,_ in exports:
            env={**os.environ,'INKSCAPE_PROFILE_DIR':str(out/'inkscape-profile')}
            subprocess.run(['inkscape',str(svg),'--export-type=png','--export-filename='+str(svg.with_suffix('.png'))],check=True,capture_output=True,env=env)
            for suffix in ['.svg','.png']:
                source=svg.with_suffix(suffix); dest=target/source.name
                if args.check:
                    if not dest.exists() or dest.read_bytes()!=source.read_bytes():
                        raise SystemExit('FAIL missing/stale export: '+str(dest))
                else: dest.write_bytes(source.read_bytes())
        if args.check:
            assert {p.name for p in target.iterdir()}=={p.with_suffix(s).name for p,_ in exports for s in ['.svg','.png']}
        print(f'PASS illustrative roster/pool/XI/captain/substitution and score chronology; {len(exports)} sheets, {sum(n for _,n in exports)} measured text bounds; '+('exports identical' if args.check else 'exports written'))


if __name__=='__main__': main()
