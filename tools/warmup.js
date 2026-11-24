// ===== voice warm-up =====
// First take: about 15 s. Hold a comfortable note in tune, then your lowest and highest comfortable notes, then
// "da da da da" back on the first note. Later takes: a quick 2-note check (skippable). Humnote then knows
//  - your tuning (so note names line up with how you actually sing),
//  - your range (a note far outside it is the tracker locking onto an overtone, not you),
//  - how crisp your syllables are (so it knows how big a "d" it needs to hear to split a repeated note).
const VP_KEY='hum2midi_voice', HP0={...Hum.HP};
function voiceProfile(){ try{ return JSON.parse(localStorage.getItem(VP_KEY)||'null'); }catch(e){ return null; } }
function saveProfile(p){ try{ localStorage.setItem(VP_KEY,JSON.stringify(p)); }catch(e){} }
const wuWant=()=>{ try{ return localStorage.getItem('hum2midi_wuQuick')!=='off'; }catch(e){ return true; } };
const WU={on:false};
const WU_STEPS={
  mid:{say:'Sing a comfortable note on “ah” and hold it in the green',need:1.6,max:9},
  low:{say:'Now slide down to your lowest comfortable note and hold it',need:1.1,max:8},
  high:{say:'Now your highest comfortable note (no straining)',need:1.1,max:8},
  da:{say:'Back to your first note: “da da da da”, a clear “d” each time',need:3.5,max:7,syll:true},
  up:{say:'Now a higher note, a few steps up, and hold it in the green',need:1.1,max:8}};
const wuName=p=>Hum.flatName(p);
async function startWarmup(mode){ try{ const had=!!rec; const R=rec||await openLive(false); if(!had) R.keep=false;
    Object.assign(WU,{on:true,mode,steps:mode==='full'?['mid','low','high','da']:['mid','up'],i:-1,res:{},prof:{...(voiceProfile()||{})}});
    $('wu').hidden=false; $('wuRes').hidden=true; $('wuGo').hidden=true; $('wuAgain').hidden=true;
    $('wuSkip').hidden=mode==='full'&&!voiceProfile(); $('wuSkip').textContent=mode==='full'?'Skip':'Skip, record now';
    $('wuTitle').textContent=mode==='full'?'Warm-up · about 15 s':'Quick check · 2 notes';
    $('wuDots').innerHTML=WU.steps.map(()=>'<i></i>').join(''); wuNext();
    $('status').textContent=mode==='full'?'Warm-up: follow the steps in the tuner.':'Quick check: two notes, then record.';
  }catch(e){ toast('Microphone blocked: allow it and try again'); WU.on=false; } }
function wuNext(){ const r=rec; WU.i++; [...$('wuDots').children].forEach((d,k)=>{ d.className=k<WU.i?'done':k===WU.i?'on':''; });
  if(WU.i>=WU.steps.length){ wuDone(); return; }
  const id=WU.steps[WU.i], S=WU_STEPS[id]; Object.assign(WU,{id,S,t0:performance.now(),hold:0,samp:[],ref:null});
  $('wuSay').textContent=S.say; $('wuBar').style.width='0%'; $('wuHint').textContent=id==='da'&&WU.res.mid?`Your first note was ${wuName(WU.res.mid.p)}.`:'';
  if(r) r.wuCap=S.syll?[]:null; }
function wuTick(r,m,steady,now,dt){ const S=WU.S; if(!S) return; const el=(now-WU.t0)/1000;
  if(S.syll){ $('wuBar').style.width=Math.min(100,100*el/S.need)+'%'; if(el>=S.need&&(isNaN(m)||el>=S.max)) wuSyll(); return; }
  // a held note: steady, in the right direction, and (for the first note) within ±25 cents of a semitone
  let good=false; if(!isNaN(m)&&steady&&r.me!=null){ const c=100*(r.me-Math.round(r.me));
    if(WU.ref!=null&&Math.abs(r.me-WU.ref)>0.8){ WU.samp=[]; WU.hold=0; WU.ref=null; }
    if(WU.ref==null) WU.ref=r.me;
    const mid=WU.res.mid, okDir=WU.id==='low'?(!mid||r.me<mid.m-1.5):(WU.id==='high'||WU.id==='up')?(!mid||r.me>mid.m+1.5):true;
    const inTune=(WU.id!=='mid'&&WU.id!=='up')||Math.abs(c)<=25;
    if(!okDir) $('wuHint').textContent=WU.id==='low'?'Go a bit lower than your first note':'Go a bit higher than your first note';
    else if(!inTune) $('wuHint').textContent=c>0?'A little sharp: come down until the tuner turns green':'A little flat: come up until the tuner turns green';
    else { $('wuHint').textContent='Good, keep holding'; good=true; } }
  if(good){ WU.hold+=dt; WU.samp.push(r.me); } else if(isNaN(m)) WU.hold=Math.max(0,WU.hold-dt*0.5);
  $('wuBar').style.width=Math.min(100,100*WU.hold/S.need)+'%';
  if(WU.hold>=S.need&&WU.samp.length){ const v=[...WU.samp].sort((a,b)=>a-b), med=v[v.length>>1], p=Math.round(med);
    let sd=0; WU.samp.forEach(x=>sd+=(x-med)**2); sd=Math.sqrt(sd/WU.samp.length);
    WU.res[WU.id]={m:med,p,c:Math.round(100*(med-p)),wob:Math.round(100*sd*1.41)}; wuNext(); }
  else if(el>S.max){ $('wuHint').textContent='Couldn’t hear a steady note, moving on'; wuNext(); } }
// the "da da da da": find each new syllable and how much louder the voice comes back after its "d"
async function wuSyll(){ const r=rec, ch=r&&r.wuCap; WU.S=null; if(r) r.wuCap=null;
  try{ const n=(ch||[]).reduce((s,c)=>s+c.length,0); if(n<r.sr*0.8) throw 0; const buf=ac().createBuffer(1,n,r.sr), d=buf.getChannelData(0); let o=0; ch.forEach(c=>{ d.set(c,o); o+=c.length; });
    WU.res.da=wuSyllables(Hum.frames(Hum.track(await toMono16k(buf),16000)),WU.res.mid&&WU.res.mid.m);
  }catch(e){ WU.res.da=null; } wuNext(); }
function wuSyllables(F,mid){ const ds=F.ds, N=F.n, rises=[];
  // only the stretch sung on (about) the first note: the end of the previous step's note doesn't count
  const vo=new Uint8Array(N); for(let i=0;i<N;i++) vo[i]=F.voiced[i]&&(mid==null||Math.abs(F.m[i]-mid)<1.6)?1:0;
  let a=0; while(a<N&&!vo[a]) a++; let b=N-1; while(b>a&&!vo[b]) b--;
  for(let i=a+6;i<b-6;i++){ let isMin=true; for(let q=i-6;q<=i+6;q++) if(ds[q]<ds[i]){ isMin=false; break; } if(!isMin) continue;
    let L=-99,R=-99; for(let q=i-15;q<i-2;q++) if(q>=a) L=Math.max(L,ds[q]); for(let q=i+2;q<i+15;q++) if(q<=b) R=Math.max(R,ds[q]);
    if(Math.min(L,R)-ds[i]>=2.5){ rises.push(R-ds[i]); i+=12; } }
  rises.sort((p,q)=>p-q); return {n:rises.length+1,rise:rises.length?rises[rises.length>>1]:0}; }
function wuDone(){ const R=WU.res, P=WU.prof, L=[]; WU.S=null;
  if(R.mid){ P.offset=Math.round((P.offset!=null&&WU.mode==='quick')?(0.5*P.offset+0.5*R.mid.c):R.mid.c); P.wobble=R.mid.wob;
    L.push(`Your note: <b>${wuName(R.mid.p)}</b>, ${Math.abs(R.mid.c)<=5?'right in tune':Math.abs(R.mid.c)+' cents '+(R.mid.c>0?'sharp':'flat')}.`); }
  if(R.up&&R.mid){ const dc=R.up.c-R.mid.c; L.push(Math.abs(dc)<=20?`Second note <b>${wuName(R.up.p)}</b>: both notes on the same tuning, so you’re on key.`:`Second note <b>${wuName(R.up.p)}</b> was ${Math.abs(dc)} cents ${dc>0?'sharper':'flatter'} than the first. Keep an eye on the tuner while you sing.`); }
  if(R.low&&R.high){ P.low=R.low.p; P.high=R.high.p; L.push(`Your range: <b>${wuName(P.low)} to ${wuName(P.high)}</b> (${P.high-P.low} semitones). Notes far outside it get checked for overtone mistakes.`); }
  if(R.mid&&R.mid.wob>=35) L.push(`You held it with a wobble of about ±${R.mid.wob} cents. That’s fine, but for exact notes sing a little straighter.`);
  if(R.da){ P.rise=Math.round(R.da.rise*10)/10; L.push(R.da.n>=3&&R.da.rise>=5?`Clear syllables (${R.da.n} heard): repeated notes will split cleanly.`:R.da.n>=3?`Soft syllables (${R.da.n} heard): Humnote will listen more closely for repeats. A crisper “d” helps.`:'I could barely hear separate syllables. Use a clear “d” or “t” for repeated notes.'); }
  const got=Object.keys(R).length>0; P.date=new Date().toISOString().slice(0,10); if(R.mid||R.low) saveProfile(P);
  $('wuTitle').textContent=got?'Ready':'Warm-up'; $('wuSay').textContent=got?'All set. Here’s what I learned:':'I couldn’t hear enough to learn from. Try again somewhere quieter?';
  $('wuBar').style.width='100%'; $('wuHint').textContent=''; $('wuRes').innerHTML=L.map(t=>`<li>${t}</li>`).join(''); $('wuRes').hidden=!L.length;
  $('wuGo').hidden=false; $('wuAgain').hidden=false; $('wuSkip').hidden=false; $('wuSkip').textContent='Close'; WU.on='done';
  $('status').textContent='Warm-up done. Press Start recording when you’re ready.'; }
function wuFinish(go){ WU.on=false; WU.S=null; if(rec) rec.wuCap=null; $('wu').hidden=true; if(go) startRec(null); else if(rec&&!rec.keep&&!rec.recording) closeLive(); }
$('wuGo').addEventListener('click',()=>wuFinish(true));
$('wuSkip').addEventListener('click',()=>{ if(WU.on==='done'){ wuFinish(false); return; } wuFinish(WU.mode==='quick'); });
$('wuAgain').addEventListener('click',()=>{ const m=WU.mode; wuFinish(false); setTimeout(()=>startWarmup(m),60); });
$('wuB').addEventListener('click',()=>{ if(rec&&rec.recording) return; if(WU.on) wuFinish(false); setTimeout(()=>startWarmup('full'),60); });
