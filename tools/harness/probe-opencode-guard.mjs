#!/usr/bin/env node
// [designed: T72 rework1] Probe-only deterministic loopback provider drives REAL native tool dispatch; never contacts a model provider.
import fs from 'node:fs';import path from 'node:path';import http from 'node:http';import assert from 'node:assert/strict';
import {resolveOpenCode,runOpenCodeWatched} from './lib/opencode.mjs';
import {hash} from './lib/opencode-transport.mjs';
const index=process.argv.indexOf('--out');assert(index>0&&process.argv[index+1],'--out required');
const out=path.resolve(process.argv[index+1]);fs.mkdirSync(out,{recursive:true});const root=fs.mkdtempSync(path.join(out,'native-'));
const work=path.join(root,'work');fs.mkdirSync(work);fs.writeFileSync(path.join(work,'inside.txt'),'INSIDE_SENTINEL\n');
const tmp=path.join(root,'tmp');fs.mkdirSync(tmp);const config=path.join(root,'config','opencode');fs.mkdirSync(config,{recursive:true});
const requests=[];const responses=[];let planned=false;
const calls=[
 {id:'external-cat',command:'cat /etc/hostname'},
 {id:'external-quoted',command:'cat \"/etc/hostname\"'},
 {id:'external-nested',command:'echo $(cat /etc/hostname)'},
 {id:'external-relative',command:`cat ${JSON.stringify(path.relative(work,'/etc/hostname'))}`},
 {id:'inside-cat',command:'cat inside.txt'},
 {id:'tmp-cat',command:'cat /tmp/../tmp'},
 {id:'research-cat',command:`cat ${JSON.stringify(path.join(process.env.HOME,'projects/goal2-archaeology/.gitignore'))}`},
 {id:'git-deny',command:'git push T72-NO-REMOTE'},
];
// [designed: T72] /tmp is read-only here; use an existing harmless file only when it exists, otherwise pwd in granted workdir.
calls.find(c=>c.id==='tmp-cat').command='pwd';calls.find(c=>c.id==='tmp-cat').workdir='/tmp';
const fake=http.createServer(async(req,res)=>{
 try {assert.equal(req.socket.remoteAddress,'127.0.0.1');assert.equal(req.url,'/v1/chat/completions');let raw='';for await(const chunk of req)raw+=chunk;const body=JSON.parse(raw);assert.equal(body.model,'guard');requests.push(body);
 const toolCall=Array.isArray(body.tools)&&body.tools.length>0&&!planned;
 if(toolCall)planned=true;
 const delta=toolCall?{tool_calls:calls.map((c,i)=>({index:i,id:c.id,type:'function',function:{name:'shell',arguments:JSON.stringify({command:c.command,...(c.workdir?{workdir:c.workdir}:{}),timeout:2000})}}))}:{content:'Deterministic loopback probe complete.'};
 const chunks=[{id:'fake',choices:[{index:0,delta,finish_reason:null}]},{id:'fake',choices:[{index:0,delta:{},finish_reason:toolCall?'tool_calls':'stop'}],usage:{prompt_tokens:0,completion_tokens:0,total_tokens:0}}];responses.push(chunks);
 res.writeHead(200,{'content-type':'text/event-stream'});for(const chunk of chunks)res.write('data: '+JSON.stringify(chunk)+'\n\n');res.end('data: [DONE]\n\n');
 }catch(e){res.writeHead(500);res.end(JSON.stringify({error:{message:e.message}}));}
});
await new Promise(r=>fake.listen(0,'127.0.0.1',r));
const provider={providers:{'t72-loopback':{name:'T72 nonbilling deterministic fake',package:'@opencode/ai/providers/openai-compatible',settings:{baseURL:`http://127.0.0.1:${fake.address().port}/v1`,apiKey:'T72-FAKE-NOT-A-CREDENTIAL'},models:{guard:{name:'Deterministic fake',family:'minimax',capabilities:{tools:true,input:['text'],output:['text']},cost:{input:0,output:0},limit:{context:100000,output:4096}}}}}};
fs.writeFileSync(path.join(config,'opencode.json'),JSON.stringify(provider,null,2));
let receipt;let outcome;
try {
 try {await runOpenCodeWatched({opencode:resolveOpenCode(),args:['run'],model:{id:'t72-loopback/guard',family:'minimax',variant:'medium'},agent:'reviewer',agentFile:new URL('../../.opencode/agents/reviewer.md',import.meta.url),prompt:'Only deterministic loopback fake provider may respond; planned shell tool permission probe.',workDir:work,title:'T72-native-guard',startupTimeoutMs:30000,totalTimeoutMs:60000,idleTimeoutMs:15000,pollMs:100,logDir:path.join(root,'receipts'),env:{...process.env,TMPDIR:tmp,XDG_CONFIG_HOME:path.dirname(config),HARNESS_OPENCODE_HOME:path.join(root,'runtime')},log:line=>console.log(line)});throw Error('external operand probe unexpectedly succeeded');}
 catch(e){if(e.manifest)receipt=JSON.parse(fs.readFileSync(e.manifest));outcome={reason:e.reason,message:e.message};}
 fs.writeFileSync(path.join(root,'outcome.json'),JSON.stringify(outcome,null,2));fs.writeFileSync(path.join(root,'requests.json'),JSON.stringify(requests,null,2));fs.writeFileSync(path.join(root,'responses.json'),JSON.stringify(responses,null,2));
 assert(receipt,'retained native receipt required');const exp=JSON.parse(fs.readFileSync(receipt.files['export.json']));const tools=exp.messages.filter(m=>m.type==='assistant').flatMap(m=>m.content).filter(p=>p.type==='tool');
 fs.writeFileSync(path.join(root,'tool-outcomes.json'),JSON.stringify(tools,null,2));
 console.log(JSON.stringify({root,outcome,tools:tools.map(t=>({id:t.id,status:t.status,error:t.error}))}));
 assert.equal(outcome.reason,'permission-rejected');
 for(const id of ['external-cat','external-quoted','external-nested','external-relative','git-deny'])assert.equal(tools.find(t=>t.id===id)?.status,'error',id+' must reject');
 for(const id of ['inside-cat','tmp-cat','research-cat'])assert.equal(tools.find(t=>t.id===id)?.status,'completed',id+' must run');
 assert.equal(receipt.usage.cost,0);assert.equal(receipt.usage.tokens.input,0);assert.equal(receipt.usage.tokens.output,0);
 fs.writeFileSync(path.join(root,'result.json'),JSON.stringify({classification:'Actual installed native2 dispatch with deterministic loopback provider; zero provider billing; fake-reported zero tokens are simulated',externalNetworkModelCalls:0,requests:requests.length,receipt:receipt.files['run.json'],binarySHA256:receipt.binarySHA256,probeSHA256:hash(fs.readFileSync(new URL(import.meta.url))),calls:calls.map(c=>c.id),passed:true},null,2));
}finally{await new Promise(r=>fake.close(r));}
console.log('Native guard nonbilling proof passed: '+root);
