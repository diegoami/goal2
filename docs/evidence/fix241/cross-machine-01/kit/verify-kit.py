"""[designed: #241] Offline package byte/syntax/envelope checks; no native execution."""
from pathlib import Path
import hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
expected=json.loads((ROOT/'inventory.json').read_text());actual={p.relative_to(ROOT).as_posix()for p in ROOT.rglob('*')if p.is_file()and p.name!='inventory.json'}
# [designed] Nested historical inventories remain ordinary package artifacts.
actual={p.relative_to(ROOT).as_posix()for p in ROOT.rglob('*')if p.is_file()and p!=ROOT/'inventory.json'}
assert set(expected)==actual
for name,want in expected.items():
 raw=(ROOT/name).read_bytes();assert sha(raw)==want,name
 assert Path(name).suffix.lower()not in {'.sav','.g2save','.dat','.exe','.dll','.so','.whl','.deb','.cmd','.bat'},name
 if name.endswith('.py'):compile(raw.decode('utf-8'),name,'exec')
 if not name.endswith('.png'):
  text=raw.decode('utf-8');assert '\r'not in text,name
  assert not re.search(r'(?:sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)',text),name
 if name.endswith('.raw-envelope.json'):
  r=json.loads(raw);assert r['encoding']=='utf-8'and sha(r['text'].encode('utf-8'))==r['sha256'],name
collection=json.loads((ROOT/'collection.json').read_text())
for name,row in collection['files'].items():assert sha((ROOT/name).read_bytes())==row['sha256'],name
print('PASS cross-machine kit:',len(expected),'files; syntax, SHA256, raw envelopes, no original/runtime asset files or credential-pattern matches')
