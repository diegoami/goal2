"""[designed: T111/T113; derived: F023, original 91CE/937C/8CCF] Brackets from structured memory views.

This draws our own labels/connections and the stored country/score data at the original's slot coordinates;
it never reads or paints the guest text page.
"""
from goal2.desktop.core_window import TextBoard
from goal2.desktop.player_card import CYAN, GOLD, GREY, WHITE, YELLOW


class BracketBoard(TextBoard):
    def __init__(self, name):
        super().__init__('CHAMPIONSHIP', 80, 20, name, 17)
        self.view = None

    def set_view(self, view, managed=()):
        self.view = view
        world = view.get('world', False)
        self.title = f"{'WORLD CUP' if world else view['continent'].upper()} / {view['year']}"
        cells = [[(' ', WHITE) for _ in range(80)] for _ in range(20)]

        def put(x, y, text, colour=WHITE):
            for i, ch in enumerate(text):
                if 1 <= x+i <= 80 and 1 <= y <= 20:cells[y-1][x+i-1] = (ch, colour)

        def horizontal(a, b, y):
            put(min(a,b), y, '─'*(abs(b-a)+1), CYAN)

        def vertical(x, a, b):
            for y in range(min(a,b), max(a,b)+1):put(x,y,'│',CYAN)

        # [designed: T113] Remove two masthead rows from World fixture coordinates to fit the same board.
        # The countries/score coordinates remain original in the structured view and its text oracle.
        slots = {s['slot']: dict(s, y=s['y']-2*world, score_y=s['score_y']-2*world) for s in view['slots']}
        # [derived: F023/91CE/937C] Stored fixtures occupy this tree; the third-place fixture is separate.
        edges = ([(k,9+(k-1)//2,(k-1)%2) for k in range(1,9)] +
                 [(k,13+(k-9)//2,(k-9)%2) for k in range(9,13)] + [(13,16,0),(14,16,1)]
                 if world else [(7,10,0),(8,10,1)])
        for source,target,index in edges:
            target_y = slots[target]['y']+index
            s=slots[source];join=s['x']+17
            horizontal(s['x']+15,join,s['y']);horizontal(s['x']+15,join,s['y']+1)
            vertical(join,min(s['y'],target_y),max(s['y']+1,target_y))
            horizontal(join,slots[target]['x']-1,target_y)
        if world:
            put(4,1,'LAST 16',GOLD);put(24,1,'QUARTERS',GOLD);put(44,1,'SEMIS',GOLD)
        else:put(slots[7]['x'],slots[7]['y']-2,'SEMI-FINALS',GOLD)
        final,third = (16,15) if world else (10,9)
        put(slots[final]['x'],slots[final]['y']-1,'FINAL',GOLD)
        # [designed: T113 review R1] Leave the semi-final score's entire byte-score width clear on this row.
        put(slots[third]['x']+(6 if world else 4),slots[third]['y']-1,'THIRD PLACE',GOLD)
        matches={m['slot']:m for m in view['matches']}
        for number,s in slots.items():
            match=matches.get(number)
            for index,(country_key,name_key) in enumerate((('first','first_name'),('second','second_name'))):
                name=match[name_key] if match else ''
                colour=YELLOW if match and match[country_key] in managed else WHITE
                put(s['x'],s['y']+index,name.rjust(15) if name else '.'*15,colour if name else GREY)
                if match and match['winner']==match[country_key]:put(s['x']+15,s['y']+index,view['winner_mark'],GOLD)
            if match and match['score'] is not None:
                put(s['score_x'],s['score_y'],f"{match['score'][0]}v{match['score'][1]}",GOLD)
        if not (world and view['places']):
            put(59,1,'TOP SCORERS',GOLD)
            for i,row in enumerate(view['top_scorers']):
                put(59,i+2,f"{i+1}) {row['name']:<13} {row['goals']:>3}",WHITE)
        if not world or view['places']:
            for i,label in enumerate(('winner','second','third')):
                y=(1 if world else 10)+2*i
                put(54,y,f'{label:<7}',GOLD)
                if i<len(view['places']):put(62,y,view['places'][i]['name'],WHITE)
        lines=[]
        for row in cells:
            parts=[]
            for ch,colour in row:
                if parts and parts[-1][1]==colour:parts[-1]=(parts[-1][0]+ch,colour)
                else:parts.append((ch,colour))
            lines.append(parts)
        self.set_lines(lines)
