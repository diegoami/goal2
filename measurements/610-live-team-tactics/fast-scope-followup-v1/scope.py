"""Discover actual selected cases without executing engine fixtures or match setup."""
import argparse,json,pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[3]))
from goal2.tests import test_watched_bench_t102 as bench
from goal2.tests import test_watched_competitive_runtime as runtime
parser=argparse.ArgumentParser();parser.add_argument('--expect',choices=('active','inactive'),required=True);args=parser.parse_args()
loader=unittest.TestLoader();groups=(bench.EngineCases,runtime.CompetitiveTests)
rows=[]
for cls in groups:
 suite=loader.loadTestsFromTestCase(cls)
 rows.append(dict(name=cls.__module__+'.'+cls.__name__,count=suite.countTestCases(),class_active=not getattr(cls,'__unittest_skip__',False)))
helpers=(bench.BenchView,runtime.ConsumerAcceptanceTests)
helper_rows=[dict(name=c.__name__,count=loader.loadTestsFromTestCase(c).countTestCases(),active=not getattr(c,'__unittest_skip__',False)) for c in helpers]
print(json.dumps(dict(groups=rows,fast_helpers=helper_rows),indent=2))
assert all(r['count']>0 for r in rows)
assert all(r['class_active']==(args.expect=='active') for r in rows),rows
assert all(r['active'] and r['count']>0 for r in helper_rows),helper_rows
