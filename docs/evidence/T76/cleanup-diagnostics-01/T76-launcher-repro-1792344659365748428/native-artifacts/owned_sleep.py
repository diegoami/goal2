import os,sys,time,json
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({'pid':os.getpid(),'ppid':os.getppid(),'executable':sys.executable,'base_executable':sys._base_executable}))
sys.stderr.write('owned diagnostic child ready\n');sys.stderr.flush()
time.sleep(60)
