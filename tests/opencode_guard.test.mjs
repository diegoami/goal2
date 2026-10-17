// [designed: T72 rework1] Legacy static operand boundaries and immutable activation selection, no model access.
import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {operandDirectories,externalEffect} from '../tools/harness/opencode-guard/scanner.mjs';
import {setup,verifyInventory} from '../tools/harness/opencode-guard/guard.mjs';
import {stageGuard,verifyPlugins} from '../tools/harness/lib/opencode-guard.mjs';
import {reviewerPolicy,trustedReviewEnv} from '../tools/harness/lib/opencode-policy.mjs';
const policy=reviewerPolicy(new URL('../.opencode/agents/reviewer.md',import.meta.url));
const root=path.resolve(fs.mkdtempSync(path.join(os.tmpdir(),'goal2-guard-')));const outside=path.resolve(root,'../outside operand');
test('legacy FILES grammar finds quoted nested relative and multi-file operands while preserving ls behavior',async()=>{
  for(const cmd of ['cat','rm','cp','mv','mkdir','touch','chmod','chown','cd']) {
    const dirs=await operandDirectories(`${cmd} '${outside}/file'`,root,[root]);assert(dirs.includes(outside),cmd+' external operand');
  }
  assert.deepEqual(await operandDirectories(`ls '${outside}'`,root,[root]),[]);
  assert.deepEqual(await operandDirectories(`echo $(cat '${outside}/file')`,root,[root]),[outside]);
  assert.deepEqual(await operandDirectories(`cat '../outside operand/file'`,root,[root]),[outside]);
  assert.deepEqual(await operandDirectories(`cat ./inside && cat '${outside}/file'`,root,[root]),[outside]);
  assert.deepEqual(await operandDirectories(`cat '${root}/inside'`,root,[root]),[]);
  await assert.rejects(()=>operandDirectories("cat 'broken",root,[root]),/unsupported shell grammar/);
});
test('same ordered external policy preserves exact tmp and research roots, rejects neighbors',()=>{
  for(const dir of ['/tmp','/tmp/opencode','/tmp/another',path.join(os.homedir(),'projects/goal2-archaeology'),path.join(os.homedir(),'projects/goal2-archaeology/sub')]) assert.equal(externalEffect(dir,policy.profile.permissions),'allow',dir);
  for(const dir of ['/etc',path.join(os.homedir(),'projects/goal2-archaeology-other')])assert.equal(externalEffect(dir,policy.profile.permissions),'ask',dir);
});
function context() {
  const o={id:'guard.test',source:'/guard/server.js',nativeIDs:['builtin'],permissions:policy.profile.permissions};
  const hooks={};const ctx={options:o,location:{directory:root},plugin:{list:async()=>({data:[{id:'builtin',source:{type:'builtin'},state:{status:'active'}},{id:o.id,source:{type:'local',path:o.source},state:{status:'active'}}]})}};
  for(const d of ['tool','permission'])ctx[d]={hook:async(n,f)=>{hooks[d+'.'+n]=f;return{dispose:async()=>{delete hooks[d+'.'+n];}};}};
  return{ctx,hooks};
}
test('native hooks tighten saved allow, preserve deny/ask and reject missing mismatched scan',async()=>{
  const {ctx,hooks}=context();const cleanup=await setup(ctx);const call={tool:'shell',sessionID:'s',id:'c',agent:'reviewer',input:{command:`cat '${outside}/file'`}};
  await hooks['tool.execute.before'](call);
  for(const effect of ['allow','ask','deny']){const e={action:'shell',sessionID:'s',agent:'reviewer',source:{id:'c'},resources:[call.input.command],effect};await hooks['permission.evaluate'](e);assert.equal(e.effect,effect==='deny'?'deny':'ask');}
  const call2={...call,id:'allowed',input:{command:'cat inside'}};await hooks['tool.execute.before'](call2);
  const event={action:'shell',sessionID:'s',agent:'reviewer',source:{id:'allowed'},resources:['cat inside'],effect:'allow'};await hooks['permission.evaluate'](event);assert.equal(event.effect,'allow');
  for(const change of [{agent:'other'},{source:{id:'missing'}},{resources:['cat /etc/file']}]){const e={...event,...change,effect:'allow'};await hooks['permission.evaluate'](e);assert.equal(e.effect,'ask');}
  await hooks['tool.execute.after'](call2);const e={...event,effect:'allow'};await hooks['permission.evaluate'](e);assert.equal(e.effect,'ask');await cleanup();
});
test('trusted activation overlay pins dependencies and rejects foreign failed duplicate or missing plugins',()=>{
  const guard=stageGuard(root,policy);const env=trustedReviewEnv({},policy,'reviewer',guard);const plugins=JSON.parse(env.OPENCODE_CONFIG_CONTENT).plugins;
  assert.equal(plugins[0],'-*','arbitrary global hooks must be disabled on every reload');assert(!plugins.includes('*'));assert(!plugins.includes('opencode.*'));
  const rows=guard.nativeIDs.map(id=>({id,source:{type:'builtin'},state:{status:'active'}}));rows.push({id:guard.id,source:{type:'local',path:guard.source},state:{status:'active'}});verifyPlugins(rows,guard);verifyInventory(rows,guard);
  for(const bad of [rows.slice(0,-1),[...rows,{id:'foreign',source:{type:'package'},state:{status:'active'}}],rows.map((r,i)=>i? r:{...r,state:{status:'failed'}}),rows.map((r,i)=>i?r:{...r,source:{type:'package'}})]) assert.throws(()=>verifyPlugins(bad,guard),/plugin|guard|builtin/);
});
