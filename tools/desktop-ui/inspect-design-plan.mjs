#!/usr/bin/env node
// [designed: #182] Inspect the local original proposal, never accept Qt behavior.
import { pathToFileURL } from 'node:url';
import { mkdir, writeFile, readFile, access } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve } from 'node:path';
import assert from 'node:assert/strict';
const modulePath=process.env.PLAYWRIGHT_MODULE;
if(!modulePath)throw new Error('Set PLAYWRIGHT_MODULE to the installed Playwright index.js');
const loaded=await import(pathToFileURL(modulePath));
const { chromium }=loaded.default??loaded;
const output=resolve(process.argv[2]||'docs/design/football-gui/evidence/browser-inspection');
try {await access(output);throw new Error(`Retain existing evidence; choose a new output directory: ${output}`);} catch(error){if(error.code!=='ENOENT')throw error;}
await mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true});
const log={scope:'Original HTML proposal only; no real Qt/SDL/Windows or engine acceptance',source:'docs/design/football-gui/index.html',checks:[],screenshots:[]};
log.source_sha256={};
for(const name of ['index.html','study.css','study.js','shirt.svg','pitch.svg'])log.source_sha256[name]=createHash('sha256').update(await readFile(resolve('docs/design/football-gui',name))).digest('hex');
try{
 const page=await browser.newPage({viewport:{width:1440,height:900},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto(pathToFileURL(resolve('docs/design/football-gui/index.html')).href);
 async function check(name,action){await action();log.checks.push(name);}
 async function shot(name){assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'shell horizontal overflow');await page.screenshot({path:resolve(output,`${name}.png`),fullPage:true});log.screenshots.push(name);}
 await check('overview has active country and supported fixture context',async()=>{await page.getByRole('heading',{name:'Netherlands',exact:true,level:1}).waitFor();assert.equal(await page.locator('#ownership').textContent(),'Active game');});
 await shot('overview-1440x900');
 await page.keyboard.press('Control+2');
 await check('keyboard page navigation focuses the squad heading',async()=>{assert.equal(await page.locator('#squad-tactics h2').evaluate(el=>el===document.activeElement),true);assert.equal(await page.locator('#roster tr').count(),20);assert.equal(await page.locator('#bench-heading').textContent(),'Bench · 9');});
 await shot('squad-1440x900');
 await page.locator('#roster input').first().uncheck();
 await check('draft changes do not confirm; invalid XI is refused',async()=>{assert.equal(await page.locator('#xi-count').textContent(),'10 / 11 selected');await page.locator('#confirm').click();assert.match(await page.locator('#status').textContent(),/Choose eleven/);});
 await page.locator('#country').selectOption('fr');
 await check('preview changes country AND roster and disables active actions',async()=>{assert.equal(await page.locator('h1').textContent(),'France');assert.match(await page.locator('#roster tr').first().textContent(),/A\. Roche/);assert.equal(await page.locator('#roster input:checked').count(),11);assert.equal(await page.locator('#confirm').isDisabled(),true);assert.equal(await page.locator('#save-action').isDisabled(),true);assert.equal(await page.locator('#play').isDisabled(),true);assert.match(await page.locator('#preview-note').textContent(),/active game: Netherlands/);});
 await page.keyboard.press('Control+1');await page.setViewportSize({width:1050,height:780});await shot('preview-1050x780');
 await page.locator('#return').click();await page.keyboard.press('Control+2');
 await check('return restores active country and unconfirmed XI draft',async()=>{assert.equal(await page.locator('h1').textContent(),'Netherlands');assert.equal(await page.locator('#roster input:checked').count(),10);await page.locator('#discard').click();assert.equal(await page.locator('#roster input:checked').count(),11);});
 await page.locator('#busy').check();
 await check('busy state locks game changes and exposes cancel',async()=>{assert.equal(await page.locator('#country').isDisabled(),true);assert.equal(await page.locator('#save-action').isDisabled(),true);assert.equal(await page.locator('#confirm').isDisabled(),true);assert.equal(await page.locator('#cancel-job').isVisible(),true);await page.locator('#cancel-job').click();assert.equal(await page.locator('#country').isDisabled(),false);});
 await page.keyboard.press('Control+4');await page.setViewportSize({width:1440,height:900});await shot('result-1440x900');
 await page.locator('#unsupported').check();
 await check('unsupported fixture refuses play and explains why',async()=>{assert.equal(await page.locator('#play').isDisabled(),true);assert.match(await page.locator('#match-result .fixture-reason').textContent(),/no supported play route/);});
 await page.locator('#unsupported').uncheck();await page.setViewportSize({width:900,height:700});await shot('result-900x700');
 await page.locator('#empty').check();
 await check('empty result has no fake event list',async()=>{assert.equal(await page.locator('.events').isVisible(),false);assert.equal(await page.locator('.empty-events').isVisible(),true);assert.equal(await page.locator('.score.last-score').textContent(),'— : —');});
 await page.setViewportSize({width:720,height:450});await page.keyboard.press('Control+2');await shot('squad-720x450-logical-space');
 await check('narrow logical space keeps draft actions and focus accessible',async()=>{await page.locator('#confirm').focus();assert.equal(await page.locator('#confirm').evaluate(el=>el===document.activeElement),true);await page.locator('#confirm').scrollIntoViewIfNeeded();assert.equal(await page.locator('#confirm').isVisible(),true);});
 await page.keyboard.press('Control+1');await page.locator('#country').selectOption('fr');await page.locator('#new').click();
 await check('only explicit new mode activates preview country',async()=>{assert.equal(await page.locator('#ownership').textContent(),'Active game');assert.equal(await page.locator('h1').textContent(),'France');assert.equal(await page.locator('#preview-note').isVisible(),false);assert.equal(await page.locator('.last-score').first().textContent(),'— : —');});
 assert.deepEqual(errors,[]);log.checks.push('no browser script errors; six screenshots without horizontal shell overflow');
 log.limitations=['Invented players/results; browser state only','720x450 is a reduced logical viewport, not proof of Windows200% scaling','Prototype does not implement all runtime contracts, source identity IDs, original result boards, pool exchange or save/resume','Real Qt/SDL and Windows evidence belongs to future T74–T79'];
 await writeFile(resolve(output,'inspection.json'),JSON.stringify(log,null,2)+'\n');
 console.log(`PASS ${log.checks.length} proposal interaction/layout checks; ${log.screenshots.length} screenshots; ${output}`);
}finally{await browser.close();}
