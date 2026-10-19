"""[designed: #254] Read-only AST proof of unchanged original behavior and assertions."""
import ast,hashlib,json,subprocess,sys
from pathlib import Path
root=Path.cwd();base='84af745c6b2d68b89077e9fde330fc8538eda031';rows=[]
def dump(node):return ast.dump(node,include_attributes=False)
def trees(name):return ast.parse(subprocess.check_output(['git','show',base+':'+name])),ast.parse((root/name).read_bytes())
class OriginalIO(ast.NodeTransformer):
 def visit_Call(self,node):
  if isinstance(node.func,ast.Name)and node.func.id=='_open_status':return ast.parse("path.open('rb')",mode='eval').body
  if isinstance(node.func,ast.Name)and node.func.id=='_replace_status':node.func=ast.Attribute(value=ast.Name(id='os',ctx=ast.Load()),attr='replace',ctx=ast.Load())
  return self.generic_visit(node)
for name,kind in(('goal2/desktop/watched.py','controller'),('goal2/desktop/pygame_viewer.py','viewer')):
 old,new=trees(name);required='_open_status'if kind=='controller'else'_status_replace_api';assert any(isinstance(n,ast.FunctionDef)and n.name==required for n in new.body),'fix254 helper absent: wrong checkout'
 new=OriginalIO().visit(new)
 if kind=='controller':
  old=next(n for n in old.body if isinstance(n,ast.ClassDef)and n.name=='WatchedController');new=next(n for n in new.body if isinstance(n,ast.ClassDef)and n.name=='WatchedController');assert dump(old)==dump(new)
 else:
  before={n.name:n for n in old.body if isinstance(n,ast.FunctionDef)};after={n.name:n for n in new.body if isinstance(n,ast.FunctionDef)}
  for key,node in before.items():assert dump(node)==dump(after[key]),key
 rows.append({'file':name,'original_AST_identical_after_reversing_only_status_IO_call':True,'current_sha256':hashlib.sha256((root/name).read_bytes()).hexdigest()})
old,new=trees('goal2/tests/test_desktop_watched_sharing.py')
def tests(tree):return {n.name:n for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)and n.name.startswith('test_')}
def assertions(node):return[dump(n)for n in ast.walk(node)if isinstance(n,ast.Assert)or isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr.startswith('assert')]
before,after=tests(old),tests(new);assert len(before)==13 and len(after)==16,'wrong sharing-test checkout'
for name,node in before.items():assert assertions(node)==assertions(after[name]),name
rows.append({'file':'goal2/tests/test_desktop_watched_sharing.py','all_original_assertions_identical':True,'existing_tests':len(before),'current_tests':len(after),'original_assertions':sum(len(assertions(n))for n in before.values())})
result={'claim':'[confirmed: AST comparisons] Original controller/viewer behavior and old assertions preserved; not native execution or independent review','result':'PASS','head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'accepted_main':base,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rows':rows};Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n');print('PASS original controller/viewer ASTs and all original sharing assertions')
