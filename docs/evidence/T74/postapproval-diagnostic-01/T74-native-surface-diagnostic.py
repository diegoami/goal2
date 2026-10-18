from pathlib import Path
import sys,os
source=Path.cwd()/'tools/desktop-ui/redesign.py'
raw=source.read_text()
old="            assert snapshot()==before,'surface inspection changed state/draft/preview/save/job ownership'"
new="""            after=snapshot()
            labels=('encoded_active','draft','active_draft','preview_identity','encoded_preview','save_bytes','save_path','path_text','match_count','starts','pending','controller_processes')
            report['surface_snapshot_delta']=[{'field':labels[i],'before':(hashlib.sha256(a).hexdigest() if isinstance(a,bytes) else repr(a)),'after':(hashlib.sha256(b).hexdigest() if isinstance(b,bytes) else repr(b))} for i,(a,b) in enumerate(zip(before,after)) if a!=b]
            assert after==before,'surface inspection changed state/draft/preview/save/job ownership: '+json.dumps(report['surface_snapshot_delta'])"""
assert raw.count(old)==1
raw=raw.replace(old,new)
trace="""            def surface_trace(stage):
                now=snapshot()
                labels=('encoded_active','draft','active_draft','preview_identity','encoded_preview','save_bytes','save_path','path_text','match_count','starts','pending','controller_processes')
                report.setdefault('surface_trace',[]).append({'stage':stage,'native_active':window.isActiveWindow(),'country':window.country.currentData(),'delta':[{'field':labels[i],'before':(hashlib.sha256(a).hexdigest() if isinstance(a,bytes) else repr(a)),'after':(hashlib.sha256(b).hexdigest() if isinstance(b,bytes) else repr(b))} for i,(a,b) in enumerate(zip(before,now)) if a!=b]})
"""
raw=raw.replace('            window.country.setFocus();app.processEvents();QTest.qWait(150)',trace+"            surface_trace('before-popup')\n            window.country.setFocus();app.processEvents();QTest.qWait(150)\n            surface_trace('country-focus')")
for target,stage in [("            assert popup.isVisible(),'native country popup did not open'",'popup-open'),("            assert not popup.isVisible(),'native country popup did not close'",'popup-escape'),("            surface('path selection'",'path-selection'),("            surface('table',",'save-restored'),("            dialog=CompetitionTable(",'other-created'),("            report['native_surfaces']=surfaces",'dialog-closed')]:
 assert raw.count(target)==1,target
 raw=raw.replace(target,"            surface_trace('"+stage+"')\n"+target)

sys.argv=[str(source),'--scenario','shell','--template','.cache/e010-r0008-halftime.sav','--data','.cache/GOAL.DAT','--evidence-dir',os.environ.get('T74_DIAGNOSTIC_OUT','.cache/main-native-surface-diagnostic-01'),'--single-scale']
exec(compile(raw,str(source),'exec'),{'__name__':'__main__','__file__':str(source)})
