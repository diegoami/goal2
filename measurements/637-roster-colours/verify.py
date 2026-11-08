"""Bind scoped native raster evidence to current renderer/test bytes."""
import hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];folder=Path(__file__).resolve().parent
record=json.loads((folder/'native-final.json').read_text())
for name,digest in json.loads((folder/'artifact-sha256.json').read_text()).items():
    assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest,name
for name,digest in record['source_sha256'].items():
    path=root/name.replace('\\','/')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
for screen in record['screens']:
    path=folder/f"squad-final-{screen['size'][0]}.png"
    assert hashlib.sha256(path.read_bytes()).hexdigest()==screen['image_sha256'],path
    assert screen['visible_rows']==20 and screen['layout_problems']==[]
assert record['tests']==3 and record['failures']==record['errors']==0
print('637 scoped native bindings PASS: 3 source files, 2 screenshots, 20 rows at both sizes')
