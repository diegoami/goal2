"""[designed: T77/M1] Audit recorded per-size coverage and historical missing-measurement negative."""
import json,sys
from pathlib import Path
r=json.loads(Path(sys.argv[1]).read_text())
assert 'table_reading_by_size' in r,'required per-supported-size table reading coverage absent'
ratio=r['ratio'];expected={(1440,900),(1050,780),(900,700)} if ratio==1 else {(900,640)}
assert {tuple(x['size']) for x in r['table_reading_by_size']}==expected
assert len(r['table_reading_by_size'])==len(expected)
def contains(a,b):return b[0]>=a[0] and b[1]>=a[1] and b[0]+b[2]<=a[0]+a[2] and b[1]+b[3]<=a[1]+a[3]
for size in r['table_reading_by_size']:
 assert size['ratio']==ratio and size['pure_state_draft_save_rng']
 assert len(size['ids'])==len(set(size['ids']))==80 and size['ids']==r['table_reading_coverage']
 assert len(size['cells'])==len({(c['id'],c['column']) for c in size['cells']})==560
 assert {(c['id'],c['column']) for c in size['cells']}=={(i,col) for i in size['ids'] for col in range(7)}
 for c in size['cells']:
  assert all(contains(c[key],c['glyph']) for key in ('cell','text_contents','table_viewport','visible_bounds'))
  assert contains(c['outer_viewport'],c['outer_glyph'])
  assert c['font_height']==c['glyph'][3] and c['font_advance']==c['glyph'][2]
 print('PASS per-size coverage',size['size'],'ratio',ratio,'80 IDs/560 unique cells; all text/viewport bounds')
