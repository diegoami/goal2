"""[designed: T76/#233] Run final regression methods against the verbatim frozen cleanup module in an isolated process."""
from pathlib import Path
import hashlib,json,subprocess,sys,unittest
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from goal2.desktop import jobs
frozen='3a76a704864fadee0a92a298af3a8a4d0072b1fa'
raw=subprocess.check_output(['git','show',frozen+':goal2/desktop/jobs.py'])
exec(compile(raw,'frozen-'+frozen+'-jobs.py','exec'),jobs.__dict__)
names=['test_transient_windows_sharing_cleanup_retries_then_releases_ownership','test_permanent_windows_sharing_is_bounded_retains_ownership_and_can_retry','test_nonsharing_cleanup_errors_propagate_without_retry_and_retain_ownership','test_failed_launch_cleanup_can_retry_without_a_process']
suite=unittest.defaultTestLoader.loadTestsFromNames(['goal2.tests.test_desktop_quick_jobs.QuickJobCases.'+name for name in names])
from goal2.tests import test_desktop_quick_jobs
assert test_desktop_quick_jobs.QuickJobs is jobs.QuickJobs
out=Path(__file__).resolve().parent
with (out/'final-tests-old-module.log').open('x') as log:result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
receipt={'tag':'[designed: T76/#233]','old_module_commit':frozen,'old_module_sha256':hashlib.sha256(raw).hexdigest(),'old_release_code_file':jobs.QuickJobs._release.__code__.co_filename,'final_tests_sha256':hashlib.sha256((ROOT/'goal2/tests/test_desktop_quick_jobs.py').read_bytes()).hexdigest(),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors)}
(out/'final-tests-old-module.json').write_text(json.dumps(receipt,indent=2)+'\n')
assert result.testsRun==4 and len(result.failures)==6 and not result.errors,receipt
print('PASS fail-before proof:4 final regression methods fail6 behavioral assertions in verbatim frozen module; no source file mutated')
