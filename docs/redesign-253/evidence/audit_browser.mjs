// [designed: #253] Read-only Chromium tour of retained browser UI; no match/save POST.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn,execFileSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
const root=process.cwd();
const config=JSON.parse(fs.readFileSync('.cache/main-environment-ready.json','utf8'));
const out=path.resolve(process.argv[2]);fs.mkdirSync(out,{recursive:false});
process.env.PLAYWRIGHT_BROWSERS_PATH=config.playwright_browsers;
const imported=await import(pathToFileURL(config.playwright_module));
const {chromium}=imported.default || imported;
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const sources=Object.fromEntries(['goal2/web/server.py','goal2/web/static/index.html','goal2/web/static/app.mjs','goal2/web/static/styles.css'].map(p=>[p,sha(p)]));
const save=path.join(root,'.cache/253-observation/browser.g2save');
const server=spawn(config.python,['-m','goal2.web','.cache/e010-r0008-halftime.sav','.cache/GOAL.DAT','--port','0','--save',save],{cwd:root,stdio:['ignore','pipe','pipe']});
let output='',errors='';server.stdout.on('data',x=>output+=x);server.stderr.on('data',x=>errors+=x);
let browser;
try{
 const until=Date.now()+10000;let url;
 while(Date.now()<until){url=output.match(/http:\/\/127\.0\.0\.1:\d+\//)?.[0];if(url)break;await new Promise(r=>setTimeout(r,50));}
 if(!url)throw Error('owned browser server did not start: '+errors.slice(-1000));
 const initial=await(await fetch(url+'api/session')).json();
 browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:900}});
 const requests=[];page.on('request',r=>{if(r.method()!=='GET')requests.push({method:r.method(),url:r.url().replace(url,'<owned-local>/')});});
 await page.goto(url);await page.waitForFunction(()=>!document.querySelector('#confirm-button').disabled);
 const screens=[];
 for(const destination of ['dashboard','squad']){
  await page.locator(`[data-page="${destination}"]`).click();
  const file='browser-'+destination+'.png';await page.screenshot({path:path.join(out,file),fullPage:true});
  screens.push({file,destination,text:await page.locator(`#${destination}-page`).innerText()});
 }
 const final=await(await fetch(url+'api/session')).json();
 const unchanged=JSON.stringify(initial)===JSON.stringify(final);
 if(!unchanged || requests.length || fs.existsSync(save))throw Error('read-only audit mutated session or wrote save');
 const report={evidence:'[confirmed: #253 direct Chromium observation]',audited_product_commit:'3335da830d289cc869f989b73816926c54360ff1',runtime_checkout_head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),browser:browser.version(),viewport:[1440,900],sources,sources_after:Object.fromEntries(Object.keys(sources).map(p=>[p,sha(p)])),resources:{template:sha('.cache/e010-r0008-halftime.sav'),data:sha('.cache/GOAL.DAT')},session_unchanged:unchanged,non_get_requests:requests,save_written:false,screens,artifacts:Object.fromEntries(screens.map(x=>[x.file,sha(path.join(out,x.file))]))};
 fs.writeFileSync(path.join(out,'report.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify({out:path.relative(root,out),browser:report.browser,session_unchanged:unchanged,non_get_requests:requests.length,screens:screens.length}));
}finally{
 if(browser)await browser.close();
 server.kill('SIGTERM');await new Promise(r=>server.once('exit',r));
}
