// [designed: T72 rework1] Tighten native shell permission outcomes using v1's grammar-based operand boundary.
import path from 'node:path';
import { operandDirectories, externalEffect } from './scanner.mjs';
export function verifyInventory(items, { id, source, nativeIDs }) {
  if (!Array.isArray(items) || items.length !== nativeIDs.length + 1) throw Error('unverified native plugin inventory');
  const expected=new Set(nativeIDs); let guard=false;
  for(const item of items) {
    if(item.state?.status !== 'active') throw Error('failed native plugin');
    if(item.id===id && item.source?.type==='local' && path.resolve(item.source.path)===source && !guard) {guard=true;continue;}
    if(item.source?.type!=='builtin' || !expected.delete(item.id)) throw Error('untrusted external plugin: '+item.id);
  }
  if(!guard || expected.size) throw Error('missing trusted native guard');
}
export async function setup(ctx) {
  const o=ctx.options;
  if(!o || !Array.isArray(o.permissions) || !Array.isArray(o.nativeIDs)) throw Error('missing trusted guard policy');
  const roots=[ctx.location.directory,ctx.location.project?.directory].filter(x=>typeof x==='string' && path.parse(x).root!==x);
  await operandDirectories('true',ctx.location.directory,roots);
  const state=new Map(); const key=e=>e.sessionID+':'+(e.id??e.source?.id);
  const inventory=async()=>{const v=await ctx.plugin.list();verifyInventory(v.data??v,o);};
  const before=await ctx.tool.hook('execute.before',async e=>{
    if(e.tool!=='shell') return;
    await inventory();
    const input=e.input; let outcome;
    try { const dirs=await operandDirectories(input.command,path.resolve(ctx.location.directory,input.workdir??'.'),roots);
      outcome=dirs.map(d=>externalEffect(d,o.permissions)).find(x=>x!=='allow')??'allow';
    }catch(error){outcome='ask';}
    state.set(key(e),{outcome,agent:e.agent,command:input?.command});
  });
  const evaluate=await ctx.permission.hook('evaluate',async e=>{
    if(e.action!=='shell') return;
    await inventory();
    const scanned=state.get(key(e));
    // [designed: T72; tests/native probe] A saved allow cannot bypass the extra operand boundary.
    if(!scanned || scanned.agent!==e.agent || !Array.isArray(e.resources) || !e.resources.every(r=>typeof r==='string' && scanned.command?.includes(r)) || scanned.outcome!=='allow') {
      if(e.effect!=='deny') e.effect=scanned?.outcome==='deny'?'deny':'ask';
      e.message='Legacy external_directory shell operand approval required; native noninteractive run must reject.';
    }
  });
  const after=await ctx.tool.hook('execute.after',e=>{if(e.tool==='shell')state.delete(key(e));});
  return async()=>{await after.dispose();await evaluate.dispose();await before.dispose();state.clear();};
}
