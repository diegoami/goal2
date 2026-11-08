"""T170a: exact reviewed import closure only; no match or campaign activation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from goal2.game.engine_python import engine_python,_is_pypy311
from goal2.game.watched_schema import ENGINE_ID,PORT_ENGINE_ID

ROOT=Path(__file__).resolve().parents[2]
EXPECTED=json.loads((ROOT/'measurements/T170a/expected-reviewed-runtime-v1.json').read_text())

CHILD=r'''
import builtins,json,sys
from pathlib import Path
assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11)
root=Path(sys.argv[1]);sys.path.insert(0,str(root))
original_import=builtins.__import__
def deny(name,*args,**kw):
 if name=='unicorn' or name.startswith('unicorn.'):raise ImportError('positive Unicorn import denial')
 return original_import(name,*args,**kw)
builtins.__import__=deny
try:__import__('unicorn')
except ImportError:pass
else:raise AssertionError('Unicorn denial inactive')
from goal2.engine.original_match import route,port
from goal2.engine.original_match.machine import Uc
assert Uc is None
assert all(callable(getattr(route,name)) for name in ('play_round','resume_round'))
assert set(route.RoundStep.__dataclass_fields__)=={'status','state','played_fixtures','news_pages','match','continuation','record'}
modules=port.available()
assert {'route','silent','news','stages','ageing','assistant'}<=set(modules)
assert not (root/'goal2/engine/original_match/assistant.py').exists(),'T183publicwrapper is not an importdependency'
entries={}
for reg,variant in port.load(['all']):
 assert variant is None
 for address,entry in reg.entries.items():
  assert address not in entries,'duplicate registry owner '+address
  entries[address]=entry
required={'000E:70B9':'ret','000E:6CA7':'ret','000E:6970':'ret 2','000E:4E0E':'ret 6',
 '1771:8208':'retf','1771:76B1':'retf','1771:6730':'ret','1771:6B55':'ret','1771:6E59':'ret',
 '1771:7090':'ret','1771:71B2':'ret','1771:74BE':'ret','000E:60CB':'retf 2','1771:80DA':'ret',
 '0791:DAF8':'retf 2','1771:55FC':'retf','0791:DEA6':'ret 2','214B:1E75':'retf',
 '0791:006C':'ret 8','1771:5BF6':'retf','1771:7812':'retf 8','23E4:0831':'retf 6','23E4:0900':'retf 4'}
for address,abi in required.items():
 assert entries[address].ret==abi and entries[address].stub is None,(address,abi)
assert 'unicorn' not in sys.modules
from goal2.game.watched_schema import ENGINE_ID,PORT_ENGINE_ID
assert ENGINE_ID=='original-match:b519d999673c9458211279fd4da8a8325b9f56fe:4'
assert PORT_ENGINE_ID=='original-match-port:b519d999673c9458211279fd4da8a8325b9f56fe:4'
print(json.dumps({'implementation':sys.implementation.name,'version':sys.version,'registry_modules':modules,
 'entries':len(entries),'required_real_entries':len(required),'unicorn_import_denied':True,
 'route_exports':True,'engine_or_match_executed':False,'public_assistant_included':False}))
'''


class SeasonVendor(unittest.TestCase):
    def test_exact_reviewed_inventory_preserves_facades_tables_and_legacy_ids(self):
        package=ROOT/'goal2/engine/original_match'
        actual={p.relative_to(ROOT).as_posix() for p in package.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
        self.assertEqual(actual,set(EXPECTED['files']))
        self.assertEqual(len(actual),50)
        for name,expected in {**EXPECTED['files'],**EXPECTED['tables']}.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),expected,name)
        manifest=json.loads((ROOT/'tools/watched-kit-hashes.json').read_text())
        self.assertEqual(manifest['source'],EXPECTED['reviewed_source'])
        self.assertEqual(manifest['files'],EXPECTED['files'])
        self.assertEqual(manifest['source_overrides'],{f'runtime/original_match/{name}.py':EXPECTED['facade_source'] for name in ('match','screens')})
        self.assertEqual(ENGINE_ID,'original-match:b519d999673c9458211279fd4da8a8325b9f56fe:4')
        self.assertEqual(PORT_ENGINE_ID,'original-match-port:b519d999673c9458211279fd4da8a8325b9f56fe:4')

    def test_complete_route_registry_imports_on_verified_pypy_with_unicorn_denied(self):
        python=engine_python();self.assertTrue(_is_pypy311(python),'candidate import must run under PyPy3.11')
        result=subprocess.run([python,'-B','-c',CHILD,str(ROOT)],cwd=ROOT,capture_output=True,text=True,timeout=120)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        observed=json.loads(result.stdout)
        self.assertTrue(observed['route_exports']);self.assertTrue(observed['unicorn_import_denied'])
        self.assertFalse(observed['engine_or_match_executed']);self.assertFalse(observed['public_assistant_included'])
        print('T170A_IMPORT '+json.dumps(observed,sort_keys=True),flush=True)

if __name__=='__main__':unittest.main()
