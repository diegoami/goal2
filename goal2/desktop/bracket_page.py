"""[designed: T111; derived: F023, original 91CE/8CCF] Continental bracket from structured memory views.

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
        self.title = f"{view['continent'].upper()} / {view['year']}"
        cells = [[(' ', WHITE) for _ in range(80)] for _ in range(20)]

        def put(x, y, text, colour=WHITE):
            for i, ch in enumerate(text):
                if 1 <= x+i <= 80 and 1 <= y <= 20:cells[y-1][x+i-1] = (ch, colour)

        def horizontal(a, b, y):
            put(min(a,b), y, '─'*(abs(b-a)+1), CYAN)

        def vertical(x, a, b):
            for y in range(min(a,b), max(a,b)+1):put(x,y,'│',CYAN)

        slots = {s['slot']: s for s in view['slots']}
        # [derived: F023/91CE] Slots 7/8 feed final 10; slot 9 is the third-place fixture.
        for source,target_y in ((7,slots[10]['y']),(8,slots[10]['y']+1)):
            s=slots[source];join=s['x']+17
            horizontal(s['x']+15,join,s['y']);vertical(join,s['y'],target_y)
            horizontal(join,slots[10]['x']-1,target_y)
        put(slots[7]['x'],slots[7]['y']-2,'SEMI-FINALS',GOLD)
        put(slots[10]['x'],slots[10]['y']-1,'FINAL',GOLD)
        put(slots[9]['x']+4,slots[9]['y']-1,'THIRD PLACE',GOLD)
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
        put(59,1,'TOP SCORERS',GOLD)
        for i,row in enumerate(view['top_scorers']):
            put(59,i+2,f"{i+1}) {row['name']:<13} {row['goals']:>3}",WHITE)
        for i,label in enumerate(('winner','second','third')):
            put(54,10+2*i,f'{label:<7}',GOLD)
            if i<len(view['places']):put(62,10+2*i,view['places'][i]['name'],WHITE)
        lines=[]
        for row in cells:
            parts=[]
            for ch,colour in row:
                if parts and parts[-1][1]==colour:parts[-1]=(parts[-1][0]+ch,colour)
                else:parts.append((ch,colour))
            lines.append(parts)
        self.set_lines(lines)
