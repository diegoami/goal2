// [designed: T72 rework1] Trusted staged native plugin, exact dependency/source identities, no cwd plugin trust.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomBytes } from 'node:crypto';
import { hash, OpenCodeInfraError, startPrivateServer, delay } from './opencode-transport.mjs';
const source=fileURLToPath(new URL('../opencode-guard/',import.meta.url));
export function stageGuard(root,policy) {
  const deps=JSON.parse(fs.readFileSync(path.join(source,'dependency-hashes.json')));
  for(const [file,expected] of Object.entries(deps)) {
    if(hash(fs.readFileSync(path.join(source,file)))!==expected) throw new OpenCodeInfraError('guard','trusted guard dependency hash mismatch: '+file);
  }
  const directory=fs.mkdtempSync(path.join(root,'native-guard-'));
  fs.cpSync(source,directory,{recursive:true});
  const id='goal2.review.guard.'+randomBytes(12).toString('hex');
  fs.writeFileSync(path.join(directory,'server.js'),`import { setup } from './guard.mjs';\nexport default {id:${JSON.stringify(id)},setup};\n`);
  const nativeIDs=JSON.parse(fs.readFileSync(path.join(directory,'native-plugins.json')));
  const files=Object.fromEntries(['guard.mjs','scanner.mjs','package.json','package-lock.json','dependency-hashes.json','native-plugins.json','server.js'].map(file=>[file,hash(fs.readFileSync(path.join(directory,file)))]));
  const guard={id,directory,source:path.join(directory,'server.js'),nativeIDs,sourceSHA256:files['guard.mjs'],files,dependencies:deps};
  guard.plugins=['-*',...nativeIDs,{package:directory,options:{id,source:guard.source,nativeIDs,permissions:policy.profile.permissions}}];
  return guard;
}
export function verifyPlugins(items,guard,{baseline=false}={}) {
  if(!Array.isArray(items) || items.length!==guard.nativeIDs.length+(baseline?0:1)) throw new OpenCodeInfraError('guard','unverified plugin inventory; external auth/provider plugins require explicit audit');
  const left=new Set(guard.nativeIDs);let found=baseline;
  for(const item of items) {
    if(item.state?.status!=='active') throw new OpenCodeInfraError('guard','failed plugin');
    if(!baseline && item.id===guard.id && item.source?.type==='local' && path.resolve(item.source.path)===guard.source && !found){found=true;continue;}
    if(item.source?.type!=='builtin' || !left.delete(item.id)) throw new OpenCodeInfraError('guard','untrusted external plugin requires explicit audit');
  }
  if(!found || left.size) throw new OpenCodeInfraError('guard','missing trusted native guard or builtin');
}
export async function readyPlugins(server,guard,{baseline=false,timeoutMs=30000}={}) {
  const start=Date.now();let last;
  do {try {const value=await server.request('/api/plugin',{timeoutMs:Math.max(1,timeoutMs-(Date.now()-start))});verifyPlugins(value.data,guard,{baseline});return value.data;}catch(e){last=e;}await delay(50);}while(Date.now()-start<timeoutMs);
  throw last;
}
export const catalogueProjection=items=>items.map(({id,modelID,providerID,family,enabled,variants})=>({id,modelID,providerID,family,enabled,variants:variants.map(v=>v.id)})).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)));
export async function baselinePlugins(cmd,{env,cwd,guard,timeoutMs=30000}) {
  const server=await startPrivateServer(cmd,{env,cwd,timeoutMs});
  let result;
  try {const plugins=await readyPlugins(server,guard,{baseline:true,timeoutMs});
    const models=catalogueProjection((await server.request('/api/model',{timeoutMs})).data);
    result={plugins,models};return result;
  }finally {const shutdown=await server.stop();if(result)result.shutdown=shutdown;}
}
