"""Discover actual scenarios without executing their setup/matches; report runtime selection."""
import argparse,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from goal2.tests.test_ui_match_day_t167 import MatchDay,HomeSide
from goal2.tests.test_ui_bench_t180 import Bench
from goal2.tests.test_watch_qualifiers_t176 import WatchQualifiers,Boundary
from goal2.tests import test_watch_qualifiers_t176_friendly as friendly
parser=argparse.ArgumentParser();parser.add_argument('--expect',choices=('active','inactive'),required=True);args=parser.parse_args()
# Discover the existing derived class rather than inventing an independent case list.
derived=[c for c in vars(friendly).values() if isinstance(c,type) and c is not WatchQualifiers and issubclass(c,WatchQualifiers)]
assert len(derived)==1,derived
classes=(MatchDay,Bench,WatchQualifiers,*derived)
loader=unittest.TestLoader();rows=[]
for cls in (*classes,HomeSide,Boundary):
 rows.append(dict(name=cls.__module__+'.'+cls.__name__,count=loader.loadTestsFromTestCase(cls).countTestCases(),active=not getattr(cls,'__unittest_skip__',False),reason=getattr(cls,'__unittest_skip_why__',None)))
print(json.dumps(rows,indent=2))
assert sum(row['count'] for row in rows[:4])==40,rows
assert sum(row['count'] for row in rows[4:])==4 and all(row['active'] for row in rows[4:]),rows
assert all(row['active']==(args.expect=='active') for row in rows[:4]),rows
