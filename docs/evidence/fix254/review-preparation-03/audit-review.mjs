// [designed: #254] Main audit preparation; an audited export is not a substitute for reading its full findings.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {normalizeSession} from '/home/diego/projects/goal2/tools/harness/lib/opencode-protocol.mjs';
import {reviewerPolicy,verifyReviewer} from '/home/diego/projects/goal2/tools/harness/lib/opencode-policy.mjs';
const root='/home/diego/projects/goal2';
const prep=path.dirname(new URL(import.meta.url).pathname);
const [filename,configName,output]=process.argv.slice(2);
assert(filename&&configName&&output,'manifest, independent expected identity config and fresh output required');
assert(!fs.existsSync(output),'preserve existing audit');
const read=p=>JSON.parse(fs.readFileSync(p));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const expected=read(configName), manifest=read(filename);
assert.match(expected.head,/^[0-9a-f]{40}$/);
assert.match(expected.nativeReceiptSHA256,/^[0-9a-f]{64}$/);
assert.equal(expected.task,'fix254');assert.equal(expected.pr,255);
assert.equal(expected.model.family==='openai',false);
assert.equal(manifest.phase,'complete');assert.equal(manifest.completed,true);assert.equal(manifest.rejected,false);
assert.equal(manifest.reviewedHead,expected.head);assert.equal(String(manifest.reviewPR),'255');assert.equal(manifest.agent,'reviewer');
assert.equal(manifest.binarySHA256,'20d305d0140bfe04df7264a4ecb014402b74b6ac0a0f6456ee07ef3325fb4a85');
assert.equal(hash(manifest.command.exe),manifest.binarySHA256);assert.deepEqual(manifest.command.prefix,[]);
assert.equal(manifest.model.id,expected.model.id);assert.equal(manifest.model.variant,expected.model.variant);
for(const [name,h]of Object.entries(manifest.artifactSHA256))assert.equal(hash(manifest.files[name]),h,`artifact ${name}`);
for(const [name,h]of Object.entries(manifest.sources))assert.equal(hash(path.resolve(root,'tools/harness/lib',name)),h,`trusted source ${name}`);
const policy=reviewerPolicy(path.join(root,'.opencode/agents/reviewer.md'));
assert.equal(policy.sourceSHA256,manifest.policySHA256);
verifyReviewer(read(manifest.files['profile.json']),policy,'reviewer');
const [providerID,...parts]=expected.model.id.split('/');
const session=normalizeSession(2,read(manifest.files['export.json']),{sessionID:manifest.sessionID,directory:manifest.directory,agent:'reviewer',model:{providerID,id:parts.join('/'),variant:expected.model.variant}});
assert.equal(session.completed,true);assert.equal(session.rejected,false);
const calls=session.messages.flatMap(m=>m.parts??[]).filter(p=>p.type==='tool');
assert.deepEqual(calls.filter(t=>t.status!=='completed'||t.error||t.rejected),[]);
const cwd=manifest.directory,cache=path.join(cwd,'.cache');
const git=(...args)=>execFileSync('git',args,{cwd,encoding:'utf8'}).trim();
assert.equal(git('rev-parse','HEAD'),expected.head);assert.equal(git('status','--porcelain','--untracked-files=no'),'');
const staged=read(path.join(cache,'main-fixtures-ready.json'));
assert.equal(staged.head,expected.head);assert.equal(staged.task,'fix254');
for(const [name,h]of Object.entries(staged.files))assert.equal(hash(path.join(cache,name)),h,`staged ${name}`);
for(const [stagedName,trusted]of Object.entries({'main-review-validation.py':'review-validation.py','main-native-proof-check.py':'native-proof-check.py','main-native-proof-controls.py':'native-proof-controls.py','main-linux-validation.py':'linux-validation01.py','main-ownership-controls.py':'linux-ownership-controls.py','main-startup-controls.py':'startup-controls.py','main-completion-controls.py':'completion-controls.py'}))assert.equal(hash(path.join(cache,stagedName)),hash(path.join(prep,trusted)),`trusted staged ${stagedName}`);
assert.equal(hash(path.join(cache,'main-native-original-receipt.json')),expected.nativeReceiptSHA256);
const native=read(path.join(cache,'main-native-original-receipt.json'));
assert.equal(native.result,'PASS');assert.equal(Object.keys(native.sources).length,181);
for(const [name,h]of Object.entries(native.sources))assert.equal(hash(path.join(cwd,name)),h,`runtime ${name}`);
const status=read(path.join(cache,'independent-review/status.json'));
assert.equal(status.phase,'complete');assert.equal(status.passed,true);assert.equal(status.owned_display_cleanup,true);
assert.equal(status.head,expected.head);assert.equal(status.native_receipt_sha256,expected.nativeReceiptSHA256);
assert.deepEqual(status.rows.map(r=>r.name),['startup-controls','completion-controls','ownership-controls','native-proof','native-proof-controls','linux-integration']);
for(const row of status.rows){assert.equal(row.exit,0);assert.equal(hash(path.join(cwd,row.log)),row.sha256,row.name);}
const linuxDir=path.join(cache,'fix254-completion-linux-01'),linux=read(path.join(linuxDir,'status.json'));
assert.equal(linux.result,'PASS');assert.equal(linux.phase,'complete');assert.equal(linux.head,expected.head);
assert.equal(linux.owned_display_cleanup,true);assert.equal(linux.private_dbus,true);
assert.deepEqual(linux.initial_sources,linux.final_sources);assert.equal(Object.keys(linux.initial_sources).length,176);
assert.deepEqual(linux.rows.map(r=>r.name),['watched-jobs','competitive-jobs','sharing','lifecycle','animated-pitch','competitive','friendlies-controls','worker','provenance','links','whitespace','authored-whitespace','premerge']);
for(const row of linux.rows){assert.equal(row.exit,0);assert.equal(row.sources_unchanged,true);assert.equal(hash(path.join(linuxDir,row.name+'.log')),row.log_sha256);}
const units=fs.readFileSync(path.join(linuxDir,'sharing.log'),'utf8');
assert(units.includes('Ran 32 tests')&&units.includes('\nOK\n')&&!units.toLowerCase().includes('skipped'));
const ownershipDir=path.join(cache,'fix254-ownership-controls01'),ownership=read(path.join(ownershipDir,'report.json'));
assert.equal(ownership.all_sources_restored,true);assert.equal(ownership.rows.length,3);
assert.equal(Object.keys(ownership.sources).length,176);
for(const [name,h]of Object.entries(ownership.sources))assert.equal(hash(path.join(cwd,name)),h,`ownership source ${name}`);
for(const row of ownership.rows){assert.notEqual(row.exit,0);assert.equal(row.intended_cleanup_assertion_failed,true);assert.equal(hash(path.join(ownershipDir,row.name+'.log')),row.log_sha256);}
for(const [dirname,count]of [['fix254-startup-controls01',4],['fix254-completion-controls01',6]]){
 const directory=path.join(cache,dirname),r=read(path.join(directory,'report.json'));
 assert.equal(r.all_sources_restored,true);assert.equal(r.rows.length,count);
 for(const row of r.rows){assert.notEqual(row.exit,0);assert.equal(hash(path.join(directory,row.name+'.log')),row.log_sha256);}
 if(typeof r.source_sha256==='string')assert.equal(hash(path.join(cwd,'goal2/game/watched_jobs.py')),r.source_sha256);
 else for(const [name,h]of Object.entries(r.source_sha256))assert.equal(hash(path.join(cwd,name)),h);
}
const controlsDir=path.join(cache,'review-native-proof-controls'),controls=read(path.join(controlsDir,'report.json'));
assert.equal(controls.result,'PASS');assert.equal(controls.source_restored,true);assert.equal(controls.rows.length,9);
assert.equal(controls.original_receipt_sha256,expected.nativeReceiptSHA256);
for(const row of controls.rows){assert.notEqual(row.exit,0);assert.equal(hash(path.join(controlsDir,row.name+'.log')),row.log_sha256);}
const final=fs.readFileSync(manifest.files['final.txt'],'utf8');
assert(final.includes(`#254 review (${expected.model.alias}), PR #255 at ${expected.head}.`),'complete canonical header required; inspect any formatting-only exception manually');
const result={result:'PASS',claim:'Main mechanical audit of complete review export, identities, permissions, hashes and independent receipts; full findings still require main adjudication',head:expected.head,session:session.sessionID,model:session.model,messages:session.messages.length,tool_calls:calls.length,rejected:session.rejected,tool_errors:0,artifact_hashes:Object.keys(manifest.artifactSHA256).length,trusted_source_hashes:Object.keys(manifest.sources).length,staged_file_hashes:Object.keys(staged.files).length,runtime_source_hashes:Object.keys(native.sources).length,linux_groups:linux.rows.length,ownership_controls:ownership.rows.length,native_controls:controls.rows.length,native_receipt_sha256:expected.nativeReceiptSHA256,final_sha256:hash(manifest.files['final.txt']),duration_ms:manifest.durationMs,usage:manifest.usage,commands:calls.filter(t=>t.name==='shell').map(t=>t.input.command)};
fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify(result,null,2));
