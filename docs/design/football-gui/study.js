/* [designed: #182] Local-only prototype state; invented samples, no game/save APIs. */
'use strict';
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const countries={nl:{name:'Netherlands',mark:'NL',color:'#f77d42',names:['A. Veld','B. Dijk','C. Bos','D. Berg','E. Strand','F. West','G. Noord','H. Groen','J. Meer','M. Duin','P. Zand','R. Dam','S. Vaart','T. Laan','V. Kade','W. Oost','Y. Water','Z. Beek','L. Brug','N. Park']},fr:{name:'France',mark:'FR',color:'#789ed6',names:['A. Roche','B. Val','C. Clair','D. Pré','E. Lac','F. Bois','G. Rive','H. Pont','J. Mont','M. Lune','P. Lys','R. Plaine','S. Vent','T. Soleil','V. Orme','W. Neige','Y. Pin','Z. Aube','L. Rose','N. Col']}};
const tactics=[[5,'Half pitch / full pitch'],[6,'Short kicks / long kicks'],[7,'Stay back / push forward'],[1,'Stay back / push forward'],[2,'Keep ball / quick pass'],[3,'Short passes / long passes'],[4,'Avoid injury / go in hard'],[8,'Zone / man to man']];
let active='nl',selected='nl',page='overview',standalone=false,busy=false,unsupported=false,empty=false;
let draft={xi:new Set(Array.from({length:11},(_,i)=>i)),captain:0,bits:0};
let confirmed={xi:new Set(draft.xi),captain:0,bits:0};
const isPreview=()=>selected!==active;
const status=message=>$('#status').textContent=message;
const group=i=>i===0||i===11?'Goalkeeper':i<5||i===12||i===13?'Defence':i<9||i===14||i===15||i===16?'Midfield':'Attack';
const viewDraft=()=>isPreview()?{xi:new Set(Array.from({length:11},(_,i)=>i)),captain:0,bits:0}:draft;
const dirty=()=>draft.captain!==confirmed.captain||draft.bits!==confirmed.bits||[...draft.xi].join(',')!==[...confirmed.xi].join(',');
function navigate(next){page=next;$$('.page').forEach(el=>el.hidden=el.id!==next);$$('nav button').forEach(el=>{if(el.dataset.page===next)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});$('#'+next+' h2').focus({preventScroll:true});}
function render(){
 const c=countries[selected],preview=isPreview(),d=viewDraft();
 document.documentElement.style.setProperty('--national',c.color);
 $('.country-stripe').style.background=selected==='nl'?'linear-gradient(90deg,#f77d42 0 30%,#f3efe2 30% 60%,#6c96ba 60%)':'linear-gradient(90deg,#789ed6 0 30%,#f3efe2 30% 60%,#dc7b76 60%)';
 $$('[data-country-name]').forEach(el=>el.textContent=c.name);$$('.home-mark').forEach(el=>el.textContent=c.mark);
 $('#ownership').textContent=preview?'Preview':'Active game';$('#ownership').style.background=preview?'#ffd17a':'#c8f279';
 $('#mini-state').textContent=preview?'Preview':'Active game';$('#context').textContent=preview?'BROWSE A NATIONAL TEAM':'YOUR NATIONAL TEAM';
 $('#preview-note').hidden=!preview;$('#preview-note').textContent=`Preview of ${c.name} · active game: ${countries[active].name}. Start a new mode to manage this country, or return to recover your draft.`;
 $('#return').hidden=!preview;$('#country').value=selected;$('#mode').textContent=standalone&&!preview?'Standalone friendly':'Campaign · 1990';
 $('#busy-note').hidden=!busy;
 for(const id of ['country','new','friendly'])$('#'+id).disabled=busy;
 for(const id of ['confirm','discard','save-action','play','captain'])$('#'+id).disabled=busy||preview;
 $('#resume-action').disabled=busy;
 $('#play').disabled=busy||preview||unsupported;
 $('#save-path').disabled=busy;
 $$('.fixture-kind').forEach(el=>el.textContent=unsupported?'Unsupported fixture':'Friendly');
 $$('.fixture-reason').forEach(el=>el.textContent=preview?'Preview only · start a new mode to play.':unsupported?'This fixture has no supported play route yet.':busy?'Match in progress.':dirty()?'Confirm or discard your draft before playing.':'Confirm management before playing.');
 const noResult=empty||preview;$$('.last-score').forEach(el=>el.textContent=noResult?'— : —':'2 : 1');
 $('.result-caption').textContent=noResult?'No match played.':'A clear result. A new challenge ahead.';
 $('.events').hidden=noResult;$('.empty-events').hidden=!noResult;$('.score-note').textContent=noResult?'No match played in this team context.':'Sample report · invented result, not a played match';
 $('.scoreboard .eyebrow').textContent=noResult?'NO RESULT YET':'FULL TIME · FRIENDLY';
 $('#overview-count').textContent=d.xi.size;$('#xi-count').textContent=`${d.xi.size} / 11 selected`;
 $$('.captain-name').forEach(el=>el.textContent=c.names[d.captain]);
 $('#draft-label').textContent=preview?'Preview · read only':dirty()?'Unconfirmed draft':'Confirmed team';
 $('#draft-title').textContent=preview?'Preview is read only':dirty()?'Unconfirmed management draft':'Management confirmed';
 $('#draft-copy').textContent=preview?'Return to the active game to recover your draft.':'Edits stay in a draft until you confirm.';
 $('#roster').replaceChildren();
 c.names.forEach((name,i)=>{
  const tr=document.createElement('tr');const tick=document.createElement('input');tick.type='checkbox';tick.checked=d.xi.has(i);tick.disabled=preview||busy;tick.setAttribute('aria-label',`${name}: starting eleven`);tick.dataset.player=i;
  tick.addEventListener('change',()=>{if(tick.checked)draft.xi.add(i);else draft.xi.delete(i);if(!draft.xi.has(draft.captain))draft.captain=[...draft.xi][0]??0;render();const control=$(`#roster input[data-player="${i}"]`);control.focus({preventScroll:true});status('Management draft changed; active game is unchanged.');});
  const td=document.createElement('td');td.append(tick);tr.append(td);
  const info=document.createElement('td');const button=document.createElement('button');button.className='player-name';button.textContent=name;button.onclick=()=>showPlayer(i);info.append(button);
  if(i===d.captain){const cap=document.createElement('span');cap.className='captain-badge';cap.textContent='C';cap.setAttribute('aria-label','Captain');info.append(cap);}
  const small=document.createElement('small');small.textContent=group(i);info.append(small);tr.append(info);
  [12+(i%4),36,16,'Available'].forEach(value=>{const cell=document.createElement('td');cell.textContent=value;if(value==='Available')cell.className='available';tr.append(cell);});$('#roster').append(tr);
 });
 $('#captain').replaceChildren();[...d.xi].forEach(i=>{const option=document.createElement('option');option.value=i;option.textContent=c.names[i];$('#captain').append(option);});$('#captain').value=d.captain;
 $('#bench-heading').textContent=`Bench · ${20-d.xi.size}`;$('#bench').textContent=c.names.filter((_,i)=>!d.xi.has(i)).join(' · ');
 $('#lineup').replaceChildren();['Goalkeeper','Defence','Midfield','Attack'].forEach(g=>{const row=document.createElement('div');row.className='pitch-group';const label=document.createElement('b');label.textContent=g;const names=document.createElement('span');names.textContent=[...d.xi].filter(i=>group(i)===g).map(i=>c.names[i]).join(' · ')||'No selected player';row.append(label,names);$('#lineup').append(row);});
 $('#tactics').replaceChildren();tactics.forEach(([bit,label])=>{const wrap=document.createElement('label');wrap.className='tactic';const check=document.createElement('input');check.type='checkbox';check.checked=!!(d.bits&(1<<(bit-1)));check.disabled=preview||busy;check.dataset.bit=bit;check.onchange=()=>{draft.bits^=1<<(bit-1);render();$(`#tactics input[data-bit="${bit}"]`).focus({preventScroll:true});status('Tactics draft changed.');};const words=document.createElement('span');words.textContent=label;const note=document.createElement('small');note.textContent=`Setting ${bit} · ${check.checked?'checked':'unchecked'}`;words.append(note);wrap.append(check,words);$('#tactics').append(wrap);});
 showPlayer(d.captain);
 if(preview||standalone){$('#pool .notice').textContent=preview?'Preview only. Exchanges are unavailable until this country becomes active.':'National pool requires a campaign; standalone has no reserves.';}
 else $('#pool .notice').textContent='Exchange availability comes from the existing campaign policy. The confirmed XI/captain are repaired and any draft is discarded.';
}
function showPlayer(i){const c=countries[selected];$('#detail-name').textContent=c.names[i];$('#detail-position').textContent=group(i)+(i===viewDraft().captain?' · Captain':'');$('#detail-ability').textContent=12+(i%4);}
$$('[data-page]').forEach(el=>el.onclick=()=>navigate(el.dataset.page));$$('[data-open]').forEach(el=>el.onclick=()=>navigate(el.dataset.open));$$('.go-squad').forEach(el=>el.onclick=()=>navigate('squad-tactics'));
$('#country').onchange=()=>{selected=$('#country').value;render();status(isPreview()?'Country preview changed; active game, save and draft are untouched.':'Returned to active game; management draft restored.');};
$('#return').onclick=()=>{selected=active;render();status('Returned to active game; management draft restored.');};
for(const id of ['new','friendly'])$('#'+id).onclick=()=>{active=selected;standalone=id==='friendly';draft={xi:new Set(Array.from({length:11},(_,i)=>i)),captain:0,bits:0};confirmed={xi:new Set(draft.xi),captain:0,bits:0};empty=true;$('#empty').checked=true;render();status('Study: selected country explicitly made active; no game/save file changed.');};
$('#captain').onchange=()=>{draft.captain=Number($('#captain').value);render();$('#captain').focus({preventScroll:true});status('Captain draft changed.');};
$('#confirm').onclick=()=>{if(isPreview()||busy)return;if(draft.xi.size!==11){status('Choose eleven distinct available players before confirming.');return;}confirmed={xi:new Set(draft.xi),captain:draft.captain,bits:draft.bits};render();status('Study: management confirmed in prototype memory only.');};
$('#discard').onclick=()=>{if(isPreview()||busy)return;draft={xi:new Set(confirmed.xi),captain:confirmed.captain,bits:confirmed.bits};render();status('Management draft discarded.');};
$('#busy').onchange=()=>{if(isPreview())selected=active;busy=$('#busy').checked;render();status(busy?'Study worker-busy state. Cancel remains available.':'Study worker-busy state ended.');};
$('#cancel-job').onclick=()=>{busy=false;$('#busy').checked=false;render();status('Study cancellation; active game/save unchanged.');};
$('#unsupported').onchange=()=>{unsupported=$('#unsupported').checked;render();};$('#empty').onchange=()=>{empty=$('#empty').checked;render();};
$('#play').onclick=()=>{if(dirty()){status('Confirm or discard management edits before playing.');return;}busy=true;$('#busy').checked=true;render();status('Study busy state; no match was simulated.');};
$('#save-action').onclick=()=>status('Study only: confirmed game would be saved; draft excluded. No file written.');$('#resume-action').onclick=()=>status('Study only: runtime validates the selected save before replacing the active game. No file read.');
document.addEventListener('keydown',event=>{if(event.ctrlKey&&/^[1-5]$/.test(event.key)){event.preventDefault();navigate(['overview','squad-tactics','pool','match-result','save'][Number(event.key)-1]);}if(event.ctrlKey&&event.key.toLowerCase()==='s'){event.preventDefault();if(busy||isPreview())status('Save unavailable in this context.');else $('#save-action').click();}});
render();
