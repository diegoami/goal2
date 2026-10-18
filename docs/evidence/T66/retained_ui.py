"""[designed: T66] Reproducible bounded validation command; no original bytes."""
import subprocess,sys
for scenario in ('management','campaign-friendlies','worker','campaign-pool','campaign-halftime'):
 command=[sys.executable,'tools/desktop-ui/acceptance.py','--scenario',scenario,'--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT']
 print('COMMAND',*command,flush=True)
 result=subprocess.run(command,timeout=240)
 if result.returncode:raise SystemExit(result.returncode)
print('PASS all5 retained Qt scenarios',flush=True)
