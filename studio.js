// Humnote Studio: the guided songwriting flow (start → tempo → key → instrument → record → review → more tracks)
// and the song workspace (all tracks together, sections, playback, export, full-screen editing).
// Everything musical comes from the existing engine in index.html through window.HN: recording, pitch detection,
// transcription, tempo + key detection, live notes, playback sounds and the note editor are reused unchanged.
// Nothing here analyses audio by itself. Test data from the developer panel is always labelled TEST / SIMULATED.
(()=>{
const H=window.HN; if(!H) return;
const $=id=>document.getElementById(id);
const esc=t=>String(t??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const on=(id,fn,ev='click')=>{ const el=$(id); if(el) el.addEventListener(ev,fn); };
const NAMES=['C','Db','D','Eb','E','F','F#','G','Ab','A','Bb','B'];
const keyLabel=k=>k?NAMES[k.tonic]+(k.mode==='minor'?' minor':' major'):'—';
const keyShort=k=>k?NAMES[k.tonic]+(k.mode==='minor'?'m':' Maj'):'Key ?';
const fmtT=s=>`${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`;
const clone=o=>JSON.parse(JSON.stringify(o));

// ---------- icons (one consistent line style)
const sv=(d,extra='')=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" ${extra}>${d}</svg>`;
const IC={
  piano:sv('<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M8 5v8M12 5v8M16 5v8M6.5 13v6M10.5 13v6M13.5 13v6M17.5 13v6"/>'),
  acoustic:sv('<path d="M14.5 3.5l6 6"/><path d="M17.5 6.5l-6 6"/><circle cx="8" cy="16" r="4.6"/><circle cx="8" cy="16" r="1.2"/>'),
  electric:sv('<path d="M15 3l6 6"/><path d="M18 6l-6.5 6.5"/><path d="M11.5 12.5L6 14l2 2-3 3.5 4.5-1 1 2.5 3.5-5z"/>'),
  bass:sv('<path d="M13 2.5l8.5 8.5"/><path d="M17.3 6.7L10 14"/><path d="M10 14c-3.2-1.4-6.6.7-6.6 3.9 0 2.6 2.4 4.3 4.9 3.4 2.8-1 3.3-4.6 1.7-7.3z"/>'),
  drums:sv('<ellipse cx="12" cy="9" rx="8" ry="3"/><path d="M4 9v7c0 1.7 3.6 3 8 3s8-1.3 8-3V9"/><path d="M7 3.5l3.5 5M17 3.5l-3.5 5"/>'),
  synth:sv('<path d="M2 12h3l2.2-6 3.6 12 3-9 2 5 1.7-2H22"/>'),
  strings:sv('<path d="M9 18V5.5l10-2.2v12.5"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="15.8" r="2.5"/>'),
  other:sv('<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.6 2.6M15.4 15.4L18 18M6 18l2.6-2.6M15.4 8.6L18 6"/>'),
  mic:sv('<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>'),
  back:sv('<path d="M15 6l-6 6 6 6"/>'),
  spark:sv('<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>'),
};
// instruments: playback sound (page synth), live-notes sound (native engine), default octave shift, colour
const INST={
  piano:{name:'Piano / Keys',snd:'piano',live:'keys',tr:0,gm:0,color:'#8b5cf6'},
  acoustic:{name:'Acoustic Guitar',snd:'guitar',live:'pluck',tr:0,gm:25,color:'#34d399'},
  electric:{name:'Electric Guitar',snd:'egtr',live:'lead',tr:0,gm:29,color:'#f472b6'},
  bass:{name:'Bass',snd:'bass',live:'bass',tr:-12,gm:33,color:'#60a5fa'},
  drums:{name:'Drums',snd:'drums',live:'pluck',tr:0,gm:0,color:'#fbbf24'},
  synth:{name:'Synth',snd:'synth',live:'lead',tr:0,gm:81,color:'#22d3ee'},
  strings:{name:'Strings',snd:'strings',live:'pad',tr:0,gm:48,color:'#fb923c'},
  other:{name:'Other',snd:'keys',live:'keys',tr:0,gm:4,color:'#a3a3c2'},
};

// ---------- the song project (one object, saved after every change; recordings saved separately)
const blank=()=>({v:1,title:'My Song',bpm:null,bpmSrc:null,ts:4,key:null,keySrc:null,chords:[],capo:0,chordInst:'guitar',nextInst:'piano',
  tracks:[],sections:[],view:'start',sel:null,created:Date.now()});
let P=blank();
const AUD=new Map(), ANA=new Map();      // track id -> recorded AudioBuffer / analysis frames (memory cache)
let saveT=0;
function save(){ setSave('Saving…'); clearTimeout(saveT); saveT=setTimeout(async()=>{ try{ await H.kv('studio:project',JSON.stringify(P)); setSave('Saved'); }catch(e){ setSave('Not saved'); } },350); }
function setSave(t){ const el=$('wsSave'); if(el) el.textContent=t==='Saved'?'✓ Saved':t; }
async function loadProject(){ try{ const j=await H.kv('studio:project'); if(j){ P={...blank(),...JSON.parse(j)}; } }catch(e){} }
async function audioOf(t){ if(AUD.has(t.id)) return AUD.get(t.id); if(!t.hasAudio) return null;
  try{ const b=await H.kv('studio:audio:'+t.id); if(b){ const buf=await H.ac().decodeAudioData(await b.arrayBuffer()); AUD.set(t.id,buf); return buf; } }catch(e){} return null; }
const cleanNote=n=>{ const o={start:+n.start,end:+n.end,pitch:n.pitch,vel:n.vel??90,cents:n.cents??0,rel:n.rel??0}; if(n.ed) o.ed=1; if(n.vibOff) o.vibOff=1;
  if(n.vib) o.vib={...n.vib,curve:Array.from(n.vib.curve||[])}; return o; };
const cloneNotes=a=>(a||[]).map(cleanNote);
const trk=id=>P.tracks.find(t=>t.id===id);
const beat=()=>60/(P.bpm||100), bar=()=>beat()*(P.ts||4);
function songEnd(){ let e=0; P.tracks.forEach(t=>t.notes.forEach(n=>{ e=Math.max(e,n.end-t.offset); })); P.sections.forEach(s=>{ e=Math.max(e,(s.start+s.len)*bar()); });
  const B=bar(); return Math.max(16*B,Math.ceil((e+B)/B)*B); }
function drumRange(t){ const ps=t.notes.map(n=>n.pitch); H.st.drumLo=ps.length?Math.min(...ps):48; H.st.drumHi=ps.length?Math.max(...ps):60; }

// ---------- song playback (the existing instrument sounds; each track through its own volume)
const SP={on:false,bag:[]};
function playSong(opt={}){ stopSong(); const ctx=H.ac(); if(ctx.state!=='running') ctx.resume(); H.loadPiano();
  const from=Math.max(0,opt.from||0), end=opt.end||songEnd(), list=opt.tracks||P.tracks, t0=ctx.currentTime+0.06, bag=[], anySolo=list.some(t=>t.solo);
  list.forEach(t=>{ if(!opt.all&&(t.mute||(anySolo&&!t.solo))) return; scheduleTrack(ctx,t,from,end,t0,ctx.destination,bag); });
  Object.assign(SP,{on:true,bag,from,end,p0:performance.now()+(t0-ctx.currentTime)*1000,onTick:opt.onTick,onEnd:opt.onEnd});
  const tick=()=>{ if(!SP.on) return; const t=from+(performance.now()-SP.p0)/1000; if(t>=end){ const cb=SP.onEnd; stopSong(); cb&&cb(); return; } SP.onTick&&SP.onTick(Math.max(from,t)); SP.raf=requestAnimationFrame(tick); };
  SP.raf=requestAnimationFrame(tick); }
function scheduleTrack(ctx,t,from,end,t0,dest,bag){ const g=ctx.createGain(); g.gain.value=t.vol??0.8; g.connect(dest); const prev=H.st.snd; H.st.snd=INST[t.instrument].snd; drumRange(t);
  t.notes.forEach(n=>{ const s=n.start-t.offset, e=n.end-t.offset; if(e<=from||s>=end) return; const a=Math.max(s,from);
    H.tone(ctx,Math.max(0,Math.min(127,n.pitch+(t.transpose||0))),t0+a-from,Math.max(0.03,Math.min(e,end)-a),n.vel||90,g,bag,null); });
  H.st.snd=prev;
  if(t.voice&&AUD.has(t.id)){ const src=ctx.createBufferSource(); src.buffer=AUD.get(t.id); const vg=ctx.createGain(); vg.gain.value=(t.vol??0.8)*0.9; src.connect(vg); vg.connect(dest);
    const bp=from+t.offset; if(bp>=0) src.start(t0,bp); else src.start(t0-bp,0); bag.push(src); } }
function stopSong(){ if(!SP.on) return; SP.on=false; cancelAnimationFrame(SP.raf); SP.bag.forEach(o=>{ try{ o.stop(); }catch(e){} }); SP.bag=[]; }

// ---------- shell: one full-window layer with a view per screen, faded between
document.body.classList.add('studio-on'); document.documentElement.dataset.theme='dark'; window.HN_block=true; H.loadPiano();
const VIEWS=['start','tempo','key','inst','rec','review','done','ws'];
const root=document.createElement('div'); root.className='studio'; root.id='studio';
root.innerHTML=VIEWS.map(v=>`<section class="s-view" data-v="${v}" hidden></section>`).join(''); document.body.appendChild(root);
const V=v=>root.querySelector(`.s-view[data-v="${v}"]`);
let cur=null, instBack='key';
const ENTER={start:vStart,tempo:vTempo,key:vKey,inst:vInst,rec:vRec,review:vReview,done:vDone,ws:vWS};
function go(v){ if(!ENTER[v]) v='start'; leave(cur); cur=v; P.view=v; save();
  root.querySelectorAll('.s-view').forEach(el=>{ const me=el.dataset.v===v;
    if(me){ el.hidden=false; requestAnimationFrame(()=>requestAnimationFrame(()=>el.classList.add('show'))); }
    else if(!el.hidden){ el.classList.remove('show'); setTimeout(()=>{ if(!el.classList.contains('show')) el.hidden=true; },300); } });
  ENTER[v](); devInfo(); }
function leave(v){ if(CAP.on) capStop(true); tMetStop(); stopSong(); if(v==='rec') recLeave(); }
root.addEventListener('click',e=>{ const b=e.target.closest('[data-back]'); if(b) go(b.dataset.back); });
const STEPS={tempo:1,key:2,inst:3,rec:4,review:5};
const stepHead=(v,title,back)=>{ const n=STEPS[v]; return `<div class="s-stephead"><button class="back ghost" data-back="${back}" aria-label="Back">${IC.back}</button><span class="t">${title}</span><span class="n">Step ${n} of 5</span></div>
  <div class="s-dots">${[1,2,3,4,5].map(i=>`<i class="${i<n?'done':i===n?'on':''}"></i>`).join('')}</div>`; };
function busy(msg){ let el=$('sGBusy'); if(!msg){ if(el) el.remove(); return; } if(!el){ el=document.createElement('div'); el.id='sGBusy'; el.className='s-busy'; el.style.position='fixed'; el.style.zIndex=95; document.body.appendChild(el); }
  el.innerHTML=`<div class="s-spin"></div><b style="color:#fff">${esc(msg)}</b>`; }

// ---------- 1. Start
function vStart(){ const has=P.tracks.length>0;
  V('start').innerHTML=`<div class="s-center s-start"><img class="logo" src="logo.svg" alt=""><h1>Let's make a song.</h1><p class="sub">We'll build it together, one step at a time.</p>
    <div class="row" style="justify-content:center">${has?`<button class="pri big" id="stCont">Continue “${esc(P.title)}”</button><button class="big" id="stNew">Start a new song</button>`:`<button class="pri big" id="stGo">Start creating</button>`}</div></div>`;
  on('stGo',()=>go('tempo')); on('stCont',()=>go('ws'));
  on('stNew',async()=>{ if(!confirm('Start a new song? The current song is cleared (your recordings stay in the recordings folder).')) return; resetAll(); go('tempo'); }); }
function resetAll(){ stopSong(); P=blank(); AUD.clear(); ANA.clear(); KY.res=null; KY.tab='sing'; TP.tap=[]; save(); }

// ---------- microphone capture for the tempo and key screens (the app's own mic + analysis)
const CAP={on:false};
async function capStart(max,onTick,onDone){ const had=!!H.rec; const R=H.rec||await H.openLive(false); if(!had) R.keep=false;
  R.wuCap=[]; Object.assign(CAP,{on:true,R,t0:performance.now(),max,onDone});
  const loop=()=>{ if(!CAP.on) return; const s=(performance.now()-CAP.t0)/1000; onTick&&onTick(s); if(s>=max){ CAP.onDone&&CAP.onDone(); return; } CAP.raf=requestAnimationFrame(loop); };
  CAP.raf=requestAnimationFrame(loop); }
async function capStop(discard){ if(!CAP.on) return null; CAP.on=false; cancelAnimationFrame(CAP.raf); const R=CAP.R, ch=R.wuCap||[]; R.wuCap=null;
  if(!R.keep&&!R.recording) H.closeLive(); if(discard) return null;
  const n=ch.reduce((a,c)=>a+c.length,0); if(n<R.sr*1.5) return {short:true};
  const buf=H.ac().createBuffer(1,n,R.sr), d=buf.getChannelData(0); let o=0; ch.forEach(c=>{ d.set(c,o); o+=c.length; });
  const x=await H.toMono16k(buf), F=await H.analyze(x,16000), notes=H.Hum.decode(F,H.Hum.tuningCurve(F),null,{}); return {notes,buf}; }
// live waveform bars from the microphone
function wave(id){ const cv=$(id); if(!cv) return; const w=cv.clientWidth, h=cv.clientHeight, d=devicePixelRatio||1; if(w<60||h<10) return; if(cv.width!==w*d){ cv.width=w*d; cv.height=h*d; }
  const c=cv.getContext('2d'); c.setTransform(d,0,0,d,0,0); c.clearRect(0,0,w,h); const R=H.rec, bars=13, gap=4, bw=(w-gap*(bars-1))/bars;
  for(let i=0;i<bars;i++){ let a=0.04; if(R&&R.ring&&CAP.on){ const L=R.ring.length, N=Math.round(R.sr*0.35), seg=Math.floor(N/bars), s0=R.w-N+i*seg; for(let k=0;k<seg;k+=8){ a=Math.max(a,Math.abs(R.ring[((s0+k)%L+L)%L])); } }
    const hh=Math.max(6,Math.min(h,a*h*3.2)), x=i*(bw+gap); c.fillStyle=`rgba(167,139,250,${0.45+0.55*Math.min(1,a*3)})`; c.beginPath(); c.roundRect?c.roundRect(x,(h-hh)/2,bw,hh,bw/2):c.rect(x,(h-hh)/2,bw,hh); c.fill(); } }

// ---------- 2. Tempo
const TP={tap:[],met:null};
function vTempo(){
  V('tempo').innerHTML=`<div class="s-center"><div class="s-card">${stepHead('tempo','Find your tempo','start')}
    <h2>Let's find your tempo.</h2><p class="sub">Sing or hum a few seconds of your song at the speed you imagine it.</p>
    <div class="s-capture"><canvas class="s-wave" id="sTw1"></canvas><button class="s-bigbtn" id="sTBtn" title="Press T to start and stop">T</button><canvas class="s-wave" id="sTw2"></canvas></div>
    <p class="s-hint" id="sTHint">Press <b>T</b> (or the button) and start singing. Press T again when you're done.</p>
    <div class="row" style="justify-content:center;margin-top:6px"><button id="sTap">Tap tempo</button><span class="small">or tap the beat on the space bar</span></div>
    <div class="s-result" id="sTRes" hidden></div>
    <div class="s-foot"><button class="ghost" id="sTSkip">Skip (use 100 BPM)</button><button class="pri big" id="sTNext" ${P.bpm?'':'disabled'}>Next: Find key →</button></div></div></div>`;
  on('sTBtn',tToggle); on('sTap',tapBeat); on('sTNext',()=>go('key')); on('sTSkip',()=>{ setBpm(100,'default'); go('key'); });
  wave('sTw1'); wave('sTw2'); if(P.bpm) showBpm(); }
async function tToggle(){ if(CAP.on) return tFinish(); TP.tap=[]; tMetStop();
  try{ await capStart(15,s=>{ $('sTHint').innerHTML=`Listening… <b>${s.toFixed(1)} s</b> — press T when you're done`; wave('sTw1'); wave('sTw2'); },tFinish); $('sTBtn').classList.add('live'); }
  catch(e){ H.toast(H.micErr(e)); } }
async function tFinish(){ const b=$('sTBtn'); if(b) b.classList.remove('live'); if($('sTHint')) $('sTHint').textContent='Finding the beat…';
  const r=await capStop(); wave('sTw1'); wave('sTw2'); const hint=$('sTHint'); if(!hint) return;
  if(!r||r.short){ hint.textContent='That was too short. Sing for at least 3 seconds.'; return; }
  const tp=r.notes.length>=4?H.Hum.tempo(r.notes):null;
  if(!tp){ hint.textContent=`I heard ${r.notes.length} note${r.notes.length===1?'':'s'}, not enough to find a beat. Try again a bit longer, or tap the tempo.`; return; }
  const M=H.Hum.meter(r.notes,tp)||{beat:tp.beat,ts:4}; P.ts=M.ts||4; setBpm(Math.round(60/M.beat),'sung');
  hint.textContent=`From ${r.notes.length} notes in ${r.buf.duration.toFixed(1)} s of your singing.`; }
function tapBeat(){ const t=performance.now(); if(TP.tap.length&&t-TP.tap[TP.tap.length-1]>2000) TP.tap=[]; TP.tap.push(t); TP.tap=TP.tap.slice(-8);
  const b=$('sTap'); if(b){ b.classList.add('on'); setTimeout(()=>b.classList.remove('on'),90); }
  if(TP.tap.length>=4){ const d=TP.tap.slice(1).map((x,i)=>x-TP.tap[i]).sort((a,b)=>a-b); setBpm(Math.round(60000/d[d.length>>1]),'tap'); }
  else if($('sTHint')) $('sTHint').textContent=`Keep tapping… (${TP.tap.length}/4)`; }
function setBpm(v,src){ P.bpm=Math.max(40,Math.min(220,Math.round(v))); if(src) P.bpmSrc=src; save(); if(cur==='tempo') showBpm(); if(TP.met){ tMetStop(); tMetStart(); } }
function showBpm(){ const R=$('sTRes'); if(!R) return; R.hidden=false;
  const head={sung:'<span class="ok">✔</span> Tempo detected from your singing',tap:'<span class="ok">✔</span> Tempo from your taps',sim:'<span class="test">SIMULATED</span> Test tempo (not from audio)',default:'Default tempo',edit:'Your tempo'}[P.bpmSrc]||'Your tempo';
  R.innerHTML=`<div class="head">${head}</div><div class="s-bpm">${P.bpm}<small>BPM</small></div>
    <div class="s-bpmrow"><button id="sTPlay">${TP.met?'■ Stop':'▶ Play tempo'}</button><button id="sTDn" aria-label="Slower">−</button><input type="number" id="sTVal" min="40" max="220" value="${P.bpm}" aria-label="BPM"><button id="sTUp" aria-label="Faster">+</button><button id="sTHalf" title="Half speed">½×</button><button id="sTDbl" title="Double speed">2×</button></div>
    ${P.ts===3?'<p class="small" style="text-align:center;margin:10px 0 0">It sounds like it\'s in 3/4 (three beats a bar).</p>':''}`;
  $('sTNext').disabled=false;
  on('sTPlay',()=>{ if(TP.met) tMetStop(); else tMetStart(); showBpm(); }); on('sTDn',()=>setBpm(P.bpm-1,'edit')); on('sTUp',()=>setBpm(P.bpm+1,'edit'));
  on('sTHalf',()=>setBpm(P.bpm/2,'edit')); on('sTDbl',()=>setBpm(P.bpm*2,'edit')); on('sTVal',e=>setBpm(+e.target.value||P.bpm,'edit'),'change'); }
function tMetStart(){ window.HN_clickOff=false; TP.met=H.startMetro(H.ac(),P.bpm); }
function tMetStop(){ if(TP.met){ TP.met.stop(); TP.met=null; } }

// ---------- 3. Key
const KY={tab:'sing',res:null,sel:0};
function vKey(){ const tab=KY.tab||'sing';
  V('key').innerHTML=`<div class="s-center"><div class="s-card">${stepHead('key','Find your key','tempo')}
    <h2>What key is your song in?</h2><p class="sub">Pick whichever is easiest for you.</p>
    <div class="s-tabs"><button data-kt="sing" class="${tab==='sing'?'on':''}">Sing to find my key</button><button data-kt="chords" class="${tab==='chords'?'on':''}">I know my chords</button><button data-kt="manual" class="${tab==='manual'?'on':''}">I already know my key</button></div>
    <div id="sKBody"></div>
    <div class="s-foot"><span class="small" id="sKCur">${P.key?'Key: <b>'+keyLabel(P.key)+'</b>':''}</span><button class="pri big" id="sKNext" ${P.key?'':'disabled'}>Next: Choose instrument →</button></div></div></div>`;
  root.querySelectorAll('[data-kt]').forEach(b=>b.onclick=()=>{ if(CAP.on) capStop(true); KY.tab=b.dataset.kt; vKey(); });
  on('sKNext',()=>{ if(P.key) H.setKey(P.key); instBack='key'; go('inst'); });
  ({sing:kSing,chords:kChords,manual:kManual})[tab](); }
function setKeyP(k,src){ P.key={tonic:k.tonic,mode:k.mode}; P.keySrc=src; save(); const c=$('sKCur'); if(c) c.innerHTML='Key: <b>'+keyLabel(P.key)+'</b>'; const n=$('sKNext'); if(n) n.disabled=false; }
function kSing(){ $('sKBody').innerHTML=`<p class="muted" style="text-align:center;margin:0">Sing a few lines of your melody, 5 to 10 seconds.</p>
    <div class="s-capture"><canvas class="s-wave" id="sKw1"></canvas><button class="s-bigbtn" id="sKBtn" aria-label="Sing">${IC.mic}</button><canvas class="s-wave" id="sKw2"></canvas></div>
    <p class="s-hint" id="sKHint">Press the microphone to start. It stops by itself after 10 seconds.</p><div class="s-result" id="sKRes" hidden></div>`;
  const ic=$('sKBtn').querySelector('svg'); if(ic){ ic.style.width='44px'; ic.style.height='44px'; }
  on('sKBtn',kToggle); wave('sKw1'); wave('sKw2'); if(KY.res) kShow(); }
async function kToggle(){ if(CAP.on) return kFinish();
  try{ await capStart(10,s=>{ $('sKHint').innerHTML=`Listening… <b>${s.toFixed(1)} s</b> (stops at 10 s, or press the mic)`; wave('sKw1'); wave('sKw2'); },kFinish); $('sKBtn').classList.add('live'); }
  catch(e){ H.toast(H.micErr(e)); } }
async function kFinish(){ const b=$('sKBtn'); if(b) b.classList.remove('live'); if($('sKHint')) $('sKHint').textContent='Listening for the key…';
  const r=await capStop(); wave('sKw1'); wave('sKw2'); const hint=$('sKHint'); if(!hint) return;
  if(!r||r.short){ hint.textContent='That was too short. Sing for 5 to 10 seconds.'; return; }
  const G=H.rankKeys(r.notes); if(!G.length){ hint.textContent='I couldn\'t hear enough notes. Try again a little louder or longer.'; return; }
  const ps=r.notes.map(n=>n.pitch).sort((a,b)=>a-b); KY.mid=ps[ps.length>>1];
  KY.res=G.slice(0,3).map(g=>({tonic:g.tonic,mode:g.mode})); KY.conf=Math.max(0.05,Math.min(0.97,0.5+(G[0].r-G[1].r)/0.3)); KY.src='sung'; KY.sel=0;
  hint.textContent=`From ${r.notes.length} notes you sang.`; setKeyP(KY.res[0],'sung'); kShow(); H.playScale(KY.res[0],KY.mid); }
function kShow(){ const R=$('sKRes'); if(!R||!KY.res) return; R.hidden=false; const g=KY.res[KY.sel||0], sim=KY.src==='sim';
  R.innerHTML=`<div class="head">${sim?'<span class="test">SIMULATED</span> Test result (not from audio)':'<span class="ok">✔</span> We think your key is'}</div>
    <div class="row" style="margin:10px 0"><span class="s-keybig">${keyLabel(g)}</span><button id="sKPlay">▶ Does this sound right?</button></div>
    ${sim?'':`<div class="s-conf">How sure <i><b style="width:${Math.round(KY.conf*100)}%"></b></i>${KY.conf>0.75?'very likely':KY.conf>0.55?'likely':'close call, listen to the others too'}</div>`}
    <div class="row" style="margin-top:12px"><span class="small">Or maybe:</span>${KY.res.map((k,i)=>i===(KY.sel||0)?'':`<button data-kalt="${i}">${keyLabel(k)}</button>`).join('')}<span style="flex:1"></span><button class="ghost" id="sKAgain">Try again</button></div>`;
  on('sKPlay',()=>H.playScale(g,KY.mid)); on('sKAgain',()=>{ KY.res=null; kSing(); });
  R.querySelectorAll('[data-kalt]').forEach(b=>b.onclick=()=>{ KY.sel=+b.dataset.kalt; setKeyP(KY.res[KY.sel],KY.src); kShow(); H.playScale(KY.res[KY.sel],KY.mid); }); }
// chords: shapes you play (+ capo) -> the chords that actually sound -> the key that fits them
const QUAL={'':[0,4,7],'m':[0,3,7],'7':[0,4,7,10],'m7':[0,3,7,10],'maj7':[0,4,7,11],'dim':[0,3,6],'sus4':[0,5,7],'sus2':[0,2,7]};
const QNAME={'':'major','m':'minor','7':'7','m7':'m7','maj7':'maj7','dim':'dim','sus4':'sus4','sus2':'sus2'};
const ROOTS=['C','C#','D','Eb','E','F','F#','G','Ab','A','Bb','B'];
const chName=c=>ROOTS[c.root]+c.q;
const sounding=()=>P.chords.map(c=>({root:(c.root+(P.chordInst==='guitar'?P.capo:0))%12,q:c.q}));
function keyFromChords(chs){ if(!chs.length) return [];
  const MAJ=[[0,''],[2,'m'],[4,'m'],[5,''],[7,''],[9,'m'],[11,'dim']], MIN=[[0,'m'],[2,'dim'],[3,''],[5,'m'],[7,'m'],[8,''],[10,''],[7,'']];
  const base=q=>q==='dim'?'dim':(q==='m'||q==='m7')?'m':'', out=[];
  for(let t=0;t<12;t++) for(const mode of ['major','minor']){ const D=mode==='major'?MAJ:MIN; let sc=0;
    chs.forEach(c=>{ const deg=((c.root-t)%12+12)%12, b=base(c.q); if(D.some(([d,q])=>d===deg&&q===b)) sc+=1; else if(D.some(([d])=>d===deg)) sc+=0.3; else sc-=0.4; });
    const tq=mode==='major'?'':'m', f=chs[0], l=chs[chs.length-1];
    if(f.root===t&&base(f.q)===tq) sc+=0.6; if(l.root===t&&base(l.q)===tq) sc+=0.8; if(mode==='major') sc+=0.05; out.push({tonic:t,mode,r:sc}); }
  return out.sort((a,b)=>b.r-a.r); }
function kChords(){ const g=P.chordInst==='guitar';
  $('sKBody').innerHTML=`<div class="row"><span class="small" style="width:96px">I'm playing</span><div class="s-seg"><button data-ci="guitar" class="${g?'on':''}">Guitar</button><button data-ci="piano" class="${g?'':'on'}">Piano</button></div></div>
    ${g?`<div class="row" style="margin-top:10px"><span class="small" style="width:96px">Capo</span><select id="sCapo">${[...Array(12)].map((_,i)=>`<option value="${i}" ${i===P.capo?'selected':''}>${i?'Capo on fret '+i:'No capo'}</option>`).join('')}</select></div>`:''}
    <p class="small" style="margin:16px 0 0">Your chord progression${g&&P.capo?' (the shapes you play)':''}</p>
    <div class="s-chords" id="sChList"></div>
    <div class="s-addchord"><select id="sChRoot" aria-label="Chord root">${ROOTS.map((r,i)=>`<option value="${i}">${r}</option>`).join('')}</select><select id="sChQ" aria-label="Chord type">${Object.keys(QUAL).map(q=>`<option value="${q}">${QNAME[q]}</option>`).join('')}</select><button id="sChAdd">+ Add chord</button>${P.chords.length?'':'<button class="ghost" id="sChEx">Try C – G – Am – F</button>'}</div>
    <div class="s-result" id="sChRes" hidden></div>`;
  root.querySelectorAll('[data-ci]').forEach(b=>b.onclick=()=>{ P.chordInst=b.dataset.ci; save(); kChords(); });
  on('sCapo',e=>{ P.capo=+e.target.value; save(); chList(); },'change');
  on('sChAdd',()=>{ P.chords.push({root:+$('sChRoot').value,q:$('sChQ').value}); save(); chList(); });
  on('sChEx',()=>{ P.chords=[{root:0,q:''},{root:7,q:''},{root:9,q:'m'},{root:5,q:''}]; save(); kChords(); });
  chList(); }
function chList(){ const L=$('sChList'); if(!L) return;
  L.innerHTML=P.chords.length?P.chords.map((c,i)=>`${i?'<span class="muted">–</span>':''}<span class="s-chip">${chName(c)}<button data-cm="${i},-1" aria-label="Move left">‹</button><button data-cm="${i},1" aria-label="Move right">›</button><button data-cx="${i}" aria-label="Remove">✕</button></span>`).join(''):'<span class="small">No chords yet. Add them in the order you play them.</span>';
  L.querySelectorAll('[data-cm]').forEach(b=>b.onclick=()=>{ const [i,d]=b.dataset.cm.split(',').map(Number), j=i+d; if(j<0||j>=P.chords.length) return; [P.chords[i],P.chords[j]]=[P.chords[j],P.chords[i]]; save(); chList(); });
  L.querySelectorAll('[data-cx]').forEach(b=>b.onclick=()=>{ P.chords.splice(+b.dataset.cx,1); save(); chList(); });
  const R=$('sChRes'); if(!P.chords.length){ R.hidden=true; return; } const S=sounding(), G=keyFromChords(S), k=G[0]; setKeyP(k,'chords'); R.hidden=false;
  const capo=P.chordInst==='guitar'&&P.capo;
  R.innerHTML=`<div class="head"><span class="ok">✔</span> Got it! This works in: <span class="s-keybig" style="font-size:22px">${keyLabel(k)}</span></div>
    ${capo?`<p class="s-sound" style="margin:8px 0 0">With capo ${P.capo}, these sound as ${S.map(chName).join(' – ')}.</p>`:''}
    <div class="row" style="margin-top:12px"><button id="sChPlay">▶ Hear the chords</button><span class="small">Not right?</span>${G.slice(1,3).map((g,i)=>`<button data-chk="${i+1}">${keyLabel(g)}</button>`).join('')}</div>`;
  on('sChPlay',()=>playChords(S)); R.querySelectorAll('[data-chk]').forEach(b=>b.onclick=()=>{ setKeyP(G[+b.dataset.chk],'chords'); }); }
function playChords(S){ S.forEach((c,i)=>setTimeout(()=>{ const ps=QUAL[c.q].map(x=>48+c.root+x); ps.push(36+c.root); ps.forEach(p=>H.pianoOn(p,72)); setTimeout(()=>ps.forEach(p=>H.pianoOff(p,true)),820); },i*900)); }
function kManual(){ const k=P.key||{tonic:0,mode:'major'};
  $('sKBody').innerHTML=`<div class="s-keys12">${NAMES.map((n,i)=>`<button data-mk="${i}" class="${P.key&&P.key.tonic===i?'on':''}">${n}</button>`).join('')}</div>
    <div class="row"><div class="s-seg"><button data-mm="major" class="${k.mode==='major'?'on':''}">Major</button><button data-mm="minor" class="${k.mode==='minor'?'on':''}">Minor</button></div><button id="sMkPlay" ${P.key?'':'disabled'}>▶ Hear the scale</button></div>`;
  root.querySelectorAll('[data-mk]').forEach(b=>b.onclick=()=>{ setKeyP({tonic:+b.dataset.mk,mode:(P.key||k).mode},'manual'); kManual(); H.playScale(P.key,57); });
  root.querySelectorAll('[data-mm]').forEach(b=>b.onclick=()=>{ setKeyP({tonic:(P.key||k).tonic,mode:b.dataset.mm},'manual'); kManual(); });
  on('sMkPlay',()=>H.playScale(P.key,57)); }

// ---------- 4. Instrument
function vInst(){ const adding=P.tracks.length>0;
  V('inst').innerHTML=`<div class="s-center" style="width:min(760px,94vw)"><div class="s-card">${stepHead('inst',adding?'Add a track':'Choose your first instrument',instBack)}
    <h2>${adding?'What would you like to add?':'What would you like to start with?'}</h2><p class="sub">You can change the instrument later without singing it again.</p>
    <div class="s-insts">${Object.entries(INST).map(([k,v])=>`<button class="s-inst ${P.nextInst===k?'on':''}" data-inst="${k}"><span style="color:${v.color}">${IC[k]}</span>${v.name}</button>`).join('')}</div>
    <p class="small" id="sIHint" style="margin:14px 0 0;min-height:20px">${P.nextInst==='drums'?'Drums: beatbox or hum the rhythm. Low sounds play the kick, middle the snare, high the hi-hat.':P.nextInst==='bass'?'Bass: sing the line where it\'s comfortable; it plays an octave lower.':''}</p>
    <div class="s-foot"><span></span><button class="pri big" id="sINext">Next: Record →</button></div></div></div>`;
  root.querySelectorAll('[data-inst]').forEach(b=>b.onclick=()=>{ P.nextInst=b.dataset.inst; save(); vInst(); });
  on('sINext',()=>go('rec')); }

// ---------- 5. Record (the app's own recorder, live notes and transcription)
const RC={count:true,click:true};
async function vRec(){ const I=INST[P.nextInst], n=P.tracks.length;
  V('rec').innerHTML=`<div class="s-recwrap"><div class="s-card">${stepHead('rec',n?`Record track ${n+1}`:'Record your first track','inst')}
    <h2>${n?`Let's record your ${I.name.toLowerCase()} part.`:"Let's record your melody."}</h2><p class="sub">Sing your part. We'll turn it into MIDI.</p>
    <div class="s-chipsrow"><span class="s-pill"><span style="color:${I.color};display:inline-flex">${IC[P.nextInst]}</span>${I.name}</span><span class="s-pill">${P.bpm||100} BPM${P.ts===3?' · 3/4':''}</span><span class="s-pill">${keyLabel(P.key)}</span>
      <span class="s-pill" id="sMic"><span class="dot" id="sMicDot"></span><span id="sMicName">Microphone</span><span class="s-meter"><i id="sMicLvl"></i></span></span></div>
    <div class="s-live"><canvas id="sRecCv"></canvas><div class="empty" id="sRecEmpty">Press record. ${RC.count?'After a one-bar count-in, sing.':'Then sing.'} Your notes appear here as you go.</div><div class="s-count" id="sCount" hidden></div>
      <div class="s-busy" id="sBusy" hidden><div class="s-spin"></div><b>Turning your voice into notes…</b><span class="small">This takes a few seconds.</span></div></div>
    <div class="s-recbar"><button class="s-recbtn" id="sRecBtn" aria-label="Record"></button><div><div class="s-recstate" id="sRecState">READY</div><div class="s-timer" id="sRecT">0:00</div></div>
      <div class="s-toggles"><label><input type="checkbox" id="sOptCount" ${RC.count?'checked':''}> Count-in (1 bar)</label><label><input type="checkbox" id="sOptClick" ${RC.click?'checked':''}> Click while recording</label><label><input type="checkbox" id="sOptLive" ${H.$('liveN').checked?'checked':''}> Hear notes live</label></div></div>
    <p class="small" style="margin:12px 0 0">Use headphones, so the microphone only hears your voice.</p></div></div>`;
  ['sMic'].forEach(()=>0); const ic=V('rec').querySelector('.s-pill svg'); if(ic){ ic.style.width='16px'; ic.style.height='16px'; }
  on('sRecBtn',()=>RC.rec?recStop():recStart());
  on('sOptCount',e=>{ RC.count=e.target.checked; },'change'); on('sOptClick',e=>{ RC.click=e.target.checked; },'change');
  on('sOptLive',e=>{ H.$('liveN').checked=e.target.checked; H.$('liveN').dispatchEvent(new Event('change')); },'change');
  // open the microphone now so its level shows (no click and no live notes until recording starts)
  H.$('metro').checked=false;
  try{ await H.openLive(false); const tr=H.rec&&H.rec.stream.getAudioTracks()[0]; $('sMicName').textContent=tr?tr.label.replace(/\s*\(.*\)\s*$/,'')||'Microphone':'Microphone'; $('sMicDot').classList.add('ok'); }
  catch(e){ $('sMicName').textContent=H.micErr(e); }
  RC.lvl=true; const lv=()=>{ if(!RC.lvl||cur!=='rec') return; const R=H.rec; if(R&&R.ring){ const L=R.ring.length, N=2048; let s=0; for(let k=0;k<N;k++){ const v=R.ring[((R.w-N+k)%L+L)%L]; s+=v*v; } const el=$('sMicLvl'); if(el) el.style.width=Math.min(100,Math.sqrt(s/N)*600)+'%'; } requestAnimationFrame(lv); }; lv(); }
async function recStart(){ const I=INST[P.nextInst];
  RC.count=$('sOptCount').checked; RC.click=$('sOptClick').checked;
  H.$('metro').checked=RC.count||RC.click; H.$('metBpm').value=P.bpm||100; window.HN_clickOff=!RC.click;    // the count-in always clicks
  H.$('liveSnd').value=I.live; H.$('liveSnd').dispatchEvent(new Event('change'));                         // live notes: this instrument's sound
  if(P.key) H.setKey(P.key);
  H.LR.canvas=$('sRecCv'); RC.prev=H.st.buf;
  await H.startRec(null); if(!H.rec||!H.rec.recording){ H.toast('Couldn\'t start recording'); return; }
  RC.rec=true; RC.t0=performance.now(); $('sRecBtn').classList.add('live'); $('sRecEmpty').hidden=true;
  const loop=()=>{ if(!RC.rec) return; const R=H.rec, M=R&&R.met; let n='';
    if(M&&RC.count){ const b=(H.ac().currentTime-M.t0)/M.beat; if(b<4) n=String(Math.max(1,Math.floor(b)+1)); }
    $('sCount').hidden=!n; $('sCount').textContent=n; $('sRecState').textContent=n?'COUNT-IN':'● RECORDING';
    const s=(performance.now()-RC.t0)/1000-(RC.count&&M?4*M.beat+0.12:0); $('sRecT').textContent=fmtT(Math.max(0,s)); RC.raf=requestAnimationFrame(loop); };
  loop(); }
async function recStop(){ RC.rec=false; cancelAnimationFrame(RC.raf); $('sCount').hidden=true; $('sRecBtn').classList.remove('live'); $('sRecBtn').disabled=true; $('sRecState').textContent='PROCESSING'; $('sBusy').hidden=false;
  try{ await H.stopRec(false); }catch(e){}
  window.HN_clickOff=false; H.$('metro').checked=false; const st=H.st;
  if(!st.buf||st.buf===RC.prev){ $('sBusy').hidden=true; $('sRecBtn').disabled=false; $('sRecState').textContent='READY'; H.toast('That was too short. Try again.'); return; }
  const T=st.tempo, viaClick=T&&T.conf===1, offset=viaClick?T.down+(RC.count?(P.ts||4)*T.beat:0):(T?T.down:0);
  const id='t'+Date.now().toString(36), I=P.nextInst, same=P.tracks.filter(t=>t.instrument===I).length;
  const t={id,name:INST[I].name.replace(' / Keys','')+(same?' '+(same+1):''),instrument:I,notes:cloneNotes(st.notes),base:cloneNotes(st.notes),q:null,offset,
    vol:0.8,mute:false,solo:false,transpose:INST[I].tr,voice:false,hasAudio:true,created:Date.now()};
  AUD.set(id,st.buf); ANA.set(id,{F:st.F}); try{ await H.kv('studio:audio:'+id,H.wav(st.buf)); }catch(e){}
  P.tracks.push(t); P.sel=id; REV.id=id; REV.hist=[]; save(); $('sBusy').hidden=true; go('review'); }
function recLeave(){ RC.lvl=false; if(RC.rec){ RC.rec=false; cancelAnimationFrame(RC.raf); H.stopRec(true); } H.LR.canvas=null; window.HN_clickOff=false; H.$('metro').checked=false; if(H.rec&&!H.rec.recording&&!H.rec.keep) H.closeLive(); }

// ---------- 6. Review: quantize, edit, retake, change instrument
const REV={id:null,hist:[]};
function vReview(){ const t=trk(REV.id||P.sel); if(!t){ go(P.tracks.length?'ws':'start'); return; } REV.id=t.id; const I=INST[t.instrument], first=P.tracks.length===1, g=t.q?t.q.grid:'off';
  V('review').innerHTML=`<div class="s-recwrap"><div class="s-card">${stepHead('review',first?'Review your melody':'Review your track','rec')}
    <h2>${first?'Your melody is ready.':`Your ${esc(t.name)} part is ready.`}</h2><p class="sub">${t.notes.length} notes, turned into MIDI from your voice. Your recording is kept too.</p>
    <div class="s-mini"><canvas id="sRvCv"></canvas></div>
    <div class="row" style="margin-top:14px"><button class="pri" id="sRvPlay">▶ Play</button>${P.tracks.length>1?'<label class="small"><input type="checkbox" id="sRvAll"> with the other tracks</label>':''}<span style="flex:1"></span>
      <button id="sRvUndo" ${REV.hist.length?'':'disabled'}>↶ Undo</button><button id="sRvRetake">⟲ Retake</button><button id="sRvEdit">✎ Edit notes</button>
      <select id="sRvInst" aria-label="Instrument">${Object.entries(INST).map(([k,v])=>`<option value="${k}" ${k===t.instrument?'selected':''}>${v.name}</option>`).join('')}</select></div>
    <div class="s-qcard"><div class="row"><b style="width:96px">Quantize</b><div class="s-seg" id="sRvQ">${[['auto','Automatic'],['8','Eighth notes'],['16','Sixteenth notes'],['3','Triplets'],['off','Off']].map(([v,l])=>`<button data-q="${v}" class="${g===v?'on':''}">${l}</button>`).join('')}</div></div>
      <div class="row" style="margin-top:12px"><span class="small" style="width:96px">Strength</span><input type="range" id="sRvStr" min="10" max="100" step="5" value="${Math.round((t.q?t.q.str:0.7)*100)}" style="width:240px" ${t.q?'':'disabled'}><span id="sRvStrV" class="small">${Math.round((t.q?t.q.str:0.7)*100)}%</span><span class="small" id="sRvQInfo" style="margin-left:10px">${qInfo(t)}</span></div></div>
    <div class="s-foot"><span></span><button class="pri big" id="sRvNext">Sounds good →</button></div></div></div>`;
  const redraw=()=>{ if(!SP.on) drawMini($('sRvCv'),[t]); }; redraw(); requestAnimationFrame(redraw); setTimeout(redraw,350);
  on('sRvPlay',()=>{ if(SP.on){ stopSong(); $('sRvPlay').textContent='▶ Play'; return; } const all=$('sRvAll')&&$('sRvAll').checked; const s0=Math.max(0,Math.min(...t.notes.map(n=>n.start-t.offset).concat([0]))-0.2);
    $('sRvPlay').textContent='■ Stop'; playSong({tracks:all?P.tracks:[t],all:!all,from:all?0:Math.max(0,s0),onTick:x=>drawMini($('sRvCv'),[t],null,x),onEnd:()=>{ if($('sRvPlay')) $('sRvPlay').textContent='▶ Play'; drawMini($('sRvCv'),[t]); }}); });
  on('sRvUndo',()=>{ const h=REV.hist.pop(); if(!h) return; Object.assign(t,h); save(); vReview(); });
  on('sRvRetake',()=>{ if(!confirm('Record this track again? These notes are replaced.')) return; P.tracks=P.tracks.filter(x=>x.id!==t.id); P.nextInst=t.instrument; save(); go('rec'); });
  on('sRvEdit',()=>openEditor(t,'review'));
  on('sRvInst',e=>{ pushRev(t); const k=e.target.value, was=INST[t.instrument]; if(t.transpose===was.tr) t.transpose=INST[k].tr; if(t.name.startsWith(was.name.replace(' / Keys',''))) t.name=INST[k].name.replace(' / Keys',''); t.instrument=k; save(); vReview(); },'change');
  root.querySelectorAll('[data-q]').forEach(b=>b.onclick=()=>{ pushRev(t); applyQ(t,b.dataset.q,(+$('sRvStr').value||70)/100); vReview(); });
  on('sRvStr',()=>{ if(!t.q) return; pushRev(t); },'pointerdown');
  on('sRvStr',e=>{ if(!t.q) return; $('sRvStrV').textContent=e.target.value+'%'; applyQ(t,t.q.grid,+e.target.value/100); drawMini($('sRvCv'),[t]); },'input');
  on('sRvNext',()=>{ stopSong(); go('done'); }); }
function pushRev(t){ REV.hist.push(clone({notes:t.notes,base:t.base,q:t.q,instrument:t.instrument,transpose:t.transpose,name:t.name})); if(REV.hist.length>30) REV.hist.shift(); const u=$('sRvUndo'); if(u) u.disabled=false; }
const DIVN={2:'eighth notes',4:'sixteenth notes',3:'triplets'};
const qInfo=t=>t.q?`${t.q.grid==='auto'?'Automatic chose ':'Snapping to '}${DIVN[t.q.div]}`:'Notes are exactly as you sang them.';
function autoDiv(ns,off){ const b=beat(), m=g=>{ let s=0; ns.forEach(n=>{ const x=(n.start-off)/g; s+=Math.abs(x-Math.round(x))*g; }); return s/Math.max(1,ns.length); };
  const e8=m(b/2), e16=m(b/4), e3=m(b/3); let d=2; if(e16<0.55*e8) d=4; if(e3<0.6*Math.min(e8,e16)) d=3; return d; }
function applyQ(t,grid,str){ if(grid==='off'){ t.notes=cloneNotes(t.base); t.q=null; save(); return; }
  const div=grid==='auto'?autoDiv(t.base,t.offset):{8:2,16:4,3:3}[grid]; t.notes=H.Hum.quantize(t.base,{beat:beat(),phase:t.offset},div,str).map(cleanNote); t.q={grid,str,div}; save(); }
// a simple piano roll of one or more tracks on the song's bar grid
function drawMini(cv,tracks,color,cursor){ if(!cv) return; const w=cv.clientWidth, h=cv.clientHeight, d=devicePixelRatio||1; if(cv.width!==Math.round(w*d)){ cv.width=Math.round(w*d); cv.height=Math.round(h*d); }
  const c=cv.getContext('2d'); c.setTransform(d,0,0,d,0,0); c.fillStyle='#121528'; c.fillRect(0,0,w,h);
  const all=tracks.flatMap(t=>t.notes.map(n=>({s:n.start-t.offset,e:n.end-t.offset,p:n.pitch+(t.transpose||0),t}))); if(!all.length){ c.fillStyle='#8d8fa8'; c.font='14px Inter'; c.fillText('No notes were heard. Try a retake, a little louder.',20,h/2); return; }
  const B=bar(), t0=Math.max(0,Math.floor(Math.min(...all.map(n=>n.s))/B)*B), t1=Math.ceil((Math.max(...all.map(n=>n.e))+0.01)/B)*B; let lo=Math.min(...all.map(n=>n.p))-2, hi=Math.max(...all.map(n=>n.p))+2; if(hi-lo<14){ const m=(hi+lo)/2; lo=Math.floor(m-7); hi=lo+14; }
  const L=46, top=22, X=s=>L+(s-t0)/(t1-t0)*(w-L-10), rh=(h-top-8)/(hi-lo+1), Y=p=>top+(hi-p)*rh;
  for(let p=lo;p<=hi;p++){ const blk=[1,3,6,8,10].includes(((p%12)+12)%12); c.fillStyle=blk?'#0f1226':'#141830'; c.fillRect(L,Y(p),w-L,rh); if(p%12===0||rh>=13){ c.fillStyle=p%12===0?'#eceaf6':'#6b6f8c'; c.font='500 10px Inter'; c.fillText(H.Hum.flatName(p),6,Y(p)+rh*0.7); } }
  for(let b=t0;b<=t1+1e-6;b+=beat()){ const isBar=Math.abs(((b/B)%1+1)%1)<1e-6||Math.abs(((b/B)%1+1)%1-1)<1e-6; c.fillStyle=isBar?'#3a3f66':'#1f2340'; c.fillRect(Math.round(X(b)),top,1,h-top);
    if(isBar){ c.fillStyle='#c4b5fd'; c.font='600 11px Inter'; c.fillText(String(Math.round(b/B)+1),X(b)+4,14); } }
  all.forEach(n=>{ const col=color||INST[n.t.instrument].color; c.fillStyle=col; c.globalAlpha=0.92; const x0=X(n.s), x1=X(n.e); c.beginPath(); c.roundRect?c.roundRect(x0,Y(n.p)+1,Math.max(3,x1-x0-1),Math.max(3,rh-2),3):c.rect(x0,Y(n.p)+1,Math.max(3,x1-x0-1),Math.max(3,rh-2)); c.fill(); c.globalAlpha=1; });
  if(cursor!=null){ c.fillStyle='#fff'; c.fillRect(X(cursor),top,2,h-top); } }

// ---------- 7. Track done: add another, or go to the song
function vDone(){ const n=P.tracks.length;
  V('done').innerHTML=`<div class="s-center"><div class="s-card"><h2>${n===1?'Your first track is ready.':`Track ${n} is ready.`}</h2><p class="sub">Add another instrument, or open the whole song to arrange it.</p>
    <div class="s-tracklist">${P.tracks.map(t=>`<div class="s-tli"><span class="sw" style="background:${INST[t.instrument].color}"></span><span style="color:${INST[t.instrument].color};display:inline-flex;width:20px">${IC[t.instrument]}</span><b>${esc(t.name)}</b><span class="small" style="margin-left:auto">${t.notes.length} notes</span></div>`).join('')}</div>
    <div class="row"><button class="pri big" id="sDAdd">+ Add a track</button><button class="big" id="sDWs">Open the song workspace →</button></div></div></div>`;
  on('sDAdd',()=>{ instBack='done'; go('inst'); }); on('sDWs',()=>go('ws')); }

// ---------- Song workspace
const WS={pxb:84,hd:230,pos:0,secSel:null,ai:true,hist:[]};
function vWS(){
  V('ws').innerHTML=`<div class="s-ws ${WS.ai?'':'noai'}" id="sWS">
    <div class="ws-head"><img class="logo" src="logo.svg" alt=""><input type="text" class="title" id="wsTitle" value="${esc(P.title)}" aria-label="Song title">
      <div class="ws-transport"><button class="play" id="wsPlay" title="Play / pause (space)">▶</button><button class="ghost" id="wsRew" title="Back to the start">⏮</button><span class="ws-pos" id="wsPos"></span></div>
      <button class="ws-chip" id="wsBpm" title="Tempo">${P.bpm||100} BPM</button><button class="ws-chip" id="wsKey" title="Key">${keyShort(P.key)}</button><button class="ghost ws-chip" id="wsUndo" title="Undo the last change" ${WS.hist.length?'':'disabled'}>↶</button>
      <span class="sp"></span><span class="ws-save" id="wsSave">✓ Saved</span><button class="pri" id="wsAdd">+ Add track</button><button id="wsExport">Export ▾</button><button class="ghost" id="wsSet" title="Settings">⚙</button><button class="ghost" id="wsAI" title="Show / hide the assistant">${IC.spark}</button></div>
    <aside class="ws-side"><h3>My song</h3><div id="wsSecs"></div><button id="wsSecAdd">+ Add section</button><div class="ws-secact" id="wsSecAct"></div></aside>
    <div class="ws-main" id="wsMain"></div>
    <aside class="ws-ai"><div class="aihead"><b>AI Assistant</b><span class="soon">Coming soon</span></div>
      <div class="msgs"><div class="bub">Soon you'll be able to shape your song just by asking. Things you'll be able to say:</div>
        <div class="ex">${['Create a guitar track.','Make the piano notes softer.','Add some reverb.','Make the chorus bigger.','Generate another melody.'].map(x=>`<button disabled>${x}</button>`).join('')}</div>
        <div class="bub me">Can you create a new track, make it guitar, and let me know when I'm ready to record?</div>
        <div class="bub">✦ Preview only: the assistant isn't switched on yet, so nothing here changes your song.</div></div>
      <div class="ask"><input type="text" placeholder="Ask anything… (coming soon)" disabled aria-label="Ask the assistant (coming soon)"><button class="pri" disabled aria-label="Send">➤</button></div></aside>
    <div class="ws-bottom" id="wsBottom" hidden></div></div>`;
  const ai=V('ws').querySelector('#wsAI svg'); if(ai){ ai.style.width='18px'; ai.style.height='18px'; }
  on('wsTitle',e=>{ P.title=e.target.value.trim()||'My Song'; save(); },'change');
  on('wsPlay',wsToggle); on('wsRew',()=>{ wsSeek(0); });
  on('wsBpm',wsBpmPop); on('wsKey',wsKeyPop); on('wsUndo',wsUndo);
  on('wsAdd',()=>{ instBack='ws'; go('inst'); }); on('wsExport',e=>{ e.stopPropagation(); exportMenu(); }); on('wsSet',settings);
  on('wsAI',()=>{ WS.ai=!WS.ai; $('sWS').classList.toggle('noai',!WS.ai); });
  on('wsSecAdd',secAdd);
  renderTL(); renderSecs(); renderBottom(); wsPosTxt(); setTimeout(()=>{ if(cur==='ws') renderTL(); },350); }
function wsSnap(){ WS.hist.push(JSON.stringify({tracks:P.tracks,sections:P.sections})); if(WS.hist.length>30) WS.hist.shift(); const u=$('wsUndo'); if(u) u.disabled=false; }
function wsUndo(){ const h=WS.hist.pop(); if(!h) return; const o=JSON.parse(h); P.tracks=o.tracks; P.sections=o.sections; save(); renderTL(); renderSecs(); renderBottom(); $('wsUndo').disabled=!WS.hist.length; }
function renderTL(){ const main=$('wsMain'); if(!main) return; const B=bar(), end=songEnd(), bars=Math.round(end/B), W=bars*WS.pxb, sl=main.scrollLeft, stp=main.scrollTop;
  main.innerHTML=`<div class="tl" style="width:${WS.hd+W}px">
    <div class="tl-ruler"><div class="tl-hd"></div><canvas id="tlRuler" style="width:${W}px;height:30px"></canvas></div>
    <div class="tl-secs"><div class="tl-hd" style="display:flex;align-items:center;padding-left:14px"><span class="small">Sections</span></div><div class="tl-seclane" id="tlSecLane" style="width:${W}px">${P.sections.map(s=>`<div class="tl-sec ${WS.secSel===s.id?'on':''}" data-sec="${s.id}" style="left:${s.start*WS.pxb+2}px;width:${s.len*WS.pxb-4}px" title="${esc(s.name)}: bars ${s.start+1}–${s.start+s.len}">${esc(s.name)}</div>`).join('')}</div></div>
    ${P.tracks.map(t=>{ const I=INST[t.instrument]; return `<div class="tl-row ${P.sel===t.id?'sel':''}" data-tr="${t.id}"><div class="tl-hd"><span class="tl-ico" style="color:${I.color}">${IC[t.instrument]}</span>
      <span class="tl-name"><b title="${esc(t.name)}">${esc(t.name)}${t.test?' <span class="test">TEST</span>':''}</b><input type="range" min="0" max="100" value="${Math.round((t.vol??0.8)*100)}" data-vol="${t.id}" aria-label="Volume of ${esc(t.name)}" title="Volume"></span>
      <span class="tl-ms"><button class="s ${t.solo?'on':''}" data-solo="${t.id}" title="Solo: hear only this">S</button><button class="m ${t.mute?'on':''}" data-mute="${t.id}" title="Mute">M</button></span></div>
      <div class="tl-reg" data-reg="${t.id}"><canvas data-cv="${t.id}" style="width:${W}px;height:75px"></canvas></div></div>`; }).join('')}
    <div class="tl-add">${P.tracks.length?'':'<span class="small">No tracks yet.</span>'}<button id="tlAdd">+ Add track</button><span class="small">Double-click a track to edit its notes full screen.</span></div>
    <div class="tl-ph" id="tlPh"></div></div>`;
  main.scrollLeft=sl; main.scrollTop=stp;
  drawRuler(W); P.tracks.forEach(t=>drawRegion(t,W)); wsPh();
  on('tlAdd',()=>{ instBack='ws'; go('inst'); });
  $('tlRuler').addEventListener('click',e=>{ const r=e.target.getBoundingClientRect(); wsSeek((e.clientX-r.left)/WS.pxb*B); });
  main.querySelectorAll('[data-reg]').forEach(el=>{ el.addEventListener('click',e=>{ const id=el.dataset.reg, r=el.getBoundingClientRect(); selTrack(id); wsSeek((e.clientX-r.left)/WS.pxb*B); });
    el.addEventListener('dblclick',()=>openEditor(trk(el.dataset.reg),'ws')); });
  main.querySelectorAll('.tl-row .tl-hd').forEach(el=>el.addEventListener('click',e=>{ if(e.target.closest('button,input')) return; selTrack(el.parentElement.dataset.tr); }));
  main.querySelectorAll('[data-vol]').forEach(el=>{ el.addEventListener('input',()=>{ const t=trk(el.dataset.vol); t.vol=+el.value/100; save(); }); });
  main.querySelectorAll('[data-solo]').forEach(b=>b.onclick=()=>{ const t=trk(b.dataset.solo); t.solo=!t.solo; save(); renderTL(); restartIfPlaying(); });
  main.querySelectorAll('[data-mute]').forEach(b=>b.onclick=()=>{ const t=trk(b.dataset.mute); t.mute=!t.mute; save(); renderTL(); restartIfPlaying(); });
  main.querySelectorAll('[data-sec]').forEach(el=>el.onclick=()=>{ WS.secSel=el.dataset.sec; renderSecs(); renderTL(); });
}
function drawRuler(W){ const cv=$('tlRuler'); if(!cv) return; const d=devicePixelRatio||1; cv.width=W*d; cv.height=30*d; const c=cv.getContext('2d'); c.setTransform(d,0,0,d,0,0);
  const bars=Math.round(W/WS.pxb), ts=P.ts||4; for(let b=0;b<=bars;b++){ const x=b*WS.pxb; c.fillStyle='#3a3f66'; c.fillRect(x,14,1,16); c.fillStyle='#c4b5fd'; c.font='600 11px Inter'; if(WS.pxb>=40||b%2===0) c.fillText(String(b+1),x+4,12);
    for(let k=1;k<ts;k++){ c.fillStyle='#262a45'; c.fillRect(x+k*WS.pxb/ts,22,1,8); } } }
function drawRegion(t,W){ const cv=V('ws').querySelector(`canvas[data-cv="${t.id}"]`); if(!cv) return; const h=75, d=devicePixelRatio||1; cv.width=W*d; cv.height=h*d; const c=cv.getContext('2d'); c.setTransform(d,0,0,d,0,0);
  const col=INST[t.instrument].color, B=bar(), X=s=>s/B*WS.pxb; for(let b=0;b*WS.pxb<=W;b++){ c.fillStyle='#161a33'; c.fillRect(b*WS.pxb,0,1,h); }
  if(!t.notes.length) return; const ns=t.notes.map(n=>({s:n.start-t.offset,e:n.end-t.offset,p:n.pitch})), lo=Math.min(...ns.map(n=>n.p)), hi=Math.max(...ns.map(n=>n.p)), span=Math.max(12,hi-lo+2), mid=(lo+hi)/2;
  const r0=Math.floor(Math.max(0,Math.min(...ns.map(n=>n.s)))/B)*B, r1=Math.ceil(Math.max(...ns.map(n=>n.e))/B)*B;
  c.fillStyle=col+'22'; c.strokeStyle=col+'88'; c.lineWidth=1; c.beginPath(); c.roundRect?c.roundRect(X(r0)+1,5,X(r1)-X(r0)-2,h-10,8):c.rect(X(r0)+1,5,X(r1)-X(r0)-2,h-10); c.fill(); c.stroke();
  const Y=p=>h/2-(p-mid)/span*(h-22), rh=Math.max(3,(h-22)/span);
  c.fillStyle=col; ns.forEach(n=>{ if(n.e<0) return; const x0=X(Math.max(0,n.s)); c.fillRect(x0,Y(n.p)-rh/2,Math.max(2,X(n.e)-x0-1),rh); }); }
function selTrack(id){ P.sel=id; save(); V('ws').querySelectorAll('.tl-row').forEach(r=>r.classList.toggle('sel',r.dataset.tr===id)); renderBottom(); }
function renderBottom(){ const el=$('wsBottom'); if(!el) return; const t=trk(P.sel); el.hidden=!t; if(!t) return; const I=INST[t.instrument], oct=Math.round((t.transpose||0)/12);
  el.innerHTML=`<div class="row"><span class="tl-ico" style="color:${I.color}">${IC[t.instrument]}</span><input type="text" id="wsTName" value="${esc(t.name)}" aria-label="Track name" style="width:180px">
    <select id="wsTInst" aria-label="Instrument">${Object.entries(INST).map(([k,v])=>`<option value="${k}" ${k===t.instrument?'selected':''}>${v.name}</option>`).join('')}</select>
    <span class="small">Octave</span><button id="wsTDn" aria-label="Octave down">−</button><b style="min-width:28px;text-align:center">${oct>0?'+':''}${oct}</b><button id="wsTUp" aria-label="Octave up">+</button>
    <label class="small"><input type="checkbox" id="wsTVoice" ${t.voice?'checked':''} ${t.hasAudio?'':'disabled'}> Also play my recorded voice</label>
    <span style="flex:1"></span><button class="pri" id="wsTEdit">✎ Edit notes</button><button class="ghost" id="wsTDel">Delete track</button></div>`;
  on('wsTName',e=>{ wsSnap(); t.name=e.target.value.trim()||t.name; save(); renderTL(); },'change');
  on('wsTInst',e=>{ wsSnap(); const k=e.target.value, was=INST[t.instrument]; if(t.transpose===was.tr) t.transpose=INST[k].tr; t.instrument=k; save(); renderTL(); renderBottom(); },'change');
  on('wsTDn',()=>{ t.transpose=(t.transpose||0)-12; save(); renderBottom(); }); on('wsTUp',()=>{ t.transpose=(t.transpose||0)+12; save(); renderBottom(); });
  on('wsTVoice',async e=>{ t.voice=e.target.checked; if(t.voice) await audioOf(t); save(); },'change');
  on('wsTEdit',()=>openEditor(t,'ws'));
  on('wsTDel',()=>{ if(!confirm(`Delete “${t.name}”? (Undo brings it back.)`)) return; wsSnap(); P.tracks=P.tracks.filter(x=>x.id!==t.id); P.sel=null; save(); renderTL(); renderBottom(); }); }
// playback in the workspace
function wsPosTxt(){ const el=$('wsPos'); if(el) el.textContent=`${fmtT(WS.pos)} / ${fmtT(songEnd())}`; }
function wsPh(){ const ph=$('tlPh'); if(ph) ph.style.left=(WS.hd+WS.pos/bar()*WS.pxb)+'px'; wsPosTxt(); }
function wsToggle(){ if(SP.on){ stopSong(); setPlayBtn(); return; } wsPlayFrom(WS.pos); }
function wsPlayFrom(t){ if(t>=songEnd()-0.05) t=0; playSong({from:t,onTick:x=>{ WS.pos=x; wsPh(); const m=$('wsMain'), X=WS.hd+x/bar()*WS.pxb; if(m&&(X>m.scrollLeft+m.clientWidth-60)) m.scrollLeft=X-WS.hd-80; },onEnd:()=>{ WS.pos=0; wsPh(); setPlayBtn(); }}); setPlayBtn(); }
function setPlayBtn(){ const b=$('wsPlay'); if(b) b.textContent=SP.on?'❚❚':'▶'; }
function wsSeek(t){ WS.pos=Math.max(0,t); wsPh(); if(SP.on) wsPlayFrom(WS.pos); }
function restartIfPlaying(){ if(SP.on&&cur==='ws') wsPlayFrom(WS.pos); }
function wsBpmPop(){ pop(`<p class="small" style="margin:0 0 8px">Tempo (BPM). Your notes keep their timing; the bar grid follows the tempo.</p><div class="row"><button id="pBDn">−</button><input type="number" id="pBV" value="${P.bpm||100}" min="40" max="220" style="width:90px"><button id="pBUp">+</button><button class="pri" id="pBOk">Set</button></div>`,()=>{
  on('pBDn',()=>{ $('pBV').value=+$('pBV').value-1; }); on('pBUp',()=>{ $('pBV').value=+$('pBV').value+1; });
  on('pBOk',()=>{ wsSnap(); P.bpm=Math.max(40,Math.min(220,Math.round(+$('pBV').value||P.bpm))); P.bpmSrc='edit'; save(); closePop(); vWS(); }); }); }
function wsKeyPop(){ pop(`<p class="small" style="margin:0 0 8px">Song key. Live notes stay in this key while you record.</p><select id="pKV">${[0,1].flatMap(m=>NAMES.map((n,i)=>{ const v=i+':'+(m?'minor':'major'); return `<option value="${v}" ${P.key&&P.key.tonic===i&&P.key.mode===(m?'minor':'major')?'selected':''}>${n} ${m?'minor':'major'}</option>`; })).join('')}</select> <button class="pri" id="pKOk">Set</button> <button id="pKFind">Find it again…</button>`,()=>{
  on('pKOk',()=>{ const [t,m]=$('pKV').value.split(':'); P.key={tonic:+t,mode:m}; P.keySrc='manual'; H.setKey(P.key); save(); closePop(); vWS(); });
  on('pKFind',()=>{ closePop(); go('key'); }); }); }
// sections: label parts of the song; duplicate and move carry the music in them along
const SECN=['Intro','Verse 1','Chorus 1','Verse 2','Chorus 2','Bridge','Chorus 3','Outro'];
function renderSecs(){ const L=$('wsSecs'); if(!L) return; const S=P.sections.slice().sort((a,b)=>a.start-b.start);
  L.innerHTML=S.length?S.map(s=>`<button class="ws-sec ${WS.secSel===s.id?'on':''}" data-ssel="${s.id}">${esc(s.name)}<small>${s.start+1}–${s.start+s.len}</small></button>`).join(''):'<p class="small" style="padding:0 8px;margin:0">Split your song into parts like Verse and Chorus whenever you like.</p>';
  L.querySelectorAll('[data-ssel]').forEach(b=>{ b.onclick=()=>{ WS.secSel=b.dataset.ssel; const s=P.sections.find(x=>x.id===WS.secSel); if(s) wsSeek(s.start*bar()); renderSecs(); renderTL(); }; b.ondblclick=()=>secRename(); });
  const A=$('wsSecAct'), s=P.sections.find(x=>x.id===WS.secSel); if(!s){ A.innerHTML=''; return; }
  A.innerHTML=`<button id="sxRen">Rename</button><button id="sxDup">Duplicate</button><button id="sxL" title="Move earlier">◀ Move</button><button id="sxR" title="Move later">Move ▶</button><button id="sxM" title="One bar shorter">− bar</button><button id="sxP" title="One bar longer">+ bar</button><button id="sxDel" class="ghost">Remove label</button>`;
  on('sxRen',secRename); on('sxDup',()=>secDup(s)); on('sxL',()=>secMove(s,-1)); on('sxR',()=>secMove(s,1));
  on('sxM',()=>{ if(s.len<=1) return; wsSnap(); s.len--; P.sections.forEach(o=>{ if(o!==s&&o.start>s.start) o.start--; }); save(); renderSecs(); renderTL(); });
  on('sxP',()=>{ wsSnap(); s.len++; P.sections.forEach(o=>{ if(o!==s&&o.start>s.start) o.start++; }); save(); renderSecs(); renderTL(); });
  on('sxDel',()=>{ wsSnap(); P.sections=P.sections.filter(o=>o!==s); WS.secSel=null; save(); renderSecs(); renderTL(); }); }
function secAdd(){ wsSnap(); const start=P.sections.reduce((a,s)=>Math.max(a,s.start+s.len),0), name=SECN[P.sections.length]||`Part ${P.sections.length+1}`, len=/Intro|Bridge|Outro/.test(name)?4:8;
  const s={id:'s'+Date.now().toString(36),name,start,len}; P.sections.push(s); WS.secSel=s.id; save(); renderSecs(); renderTL(); }
function secRename(){ const s=P.sections.find(x=>x.id===WS.secSel); if(!s) return; const b=V('ws').querySelector(`[data-ssel="${s.id}"]`); if(!b) return;
  const inp=document.createElement('input'); inp.type='text'; inp.value=s.name; inp.style.width='100%'; b.replaceWith(inp); inp.focus(); inp.select();
  const done=()=>{ const v=inp.value.trim(); if(v&&v!==s.name){ wsSnap(); s.name=v; save(); } renderSecs(); renderTL(); }; inp.onblur=done; inp.onkeydown=e=>{ if(e.key==='Enter') inp.blur(); if(e.key==='Escape'){ inp.value=s.name; inp.blur(); } }; }
function shiftContent(fn){ P.tracks.forEach(t=>['notes','base'].forEach(k=>{ if(t[k]) t[k]=fn(t[k],t).sort((a,b)=>a.start-b.start); })); }
function secDup(s){ wsSnap(); const B=bar(), a=s.start*B, e=(s.start+s.len)*B, d=s.len*B;
  shiftContent((ns,t)=>{ const out=[]; ns.forEach(n=>{ const st=n.start-t.offset; if(st>=e) out.push({...n,start:n.start+d,end:n.end+d}); else { out.push(n); if(st>=a) out.push({...clone(n),start:n.start+d,end:Math.min(n.end,t.offset+e)+d}); } }); return out; });
  P.sections.forEach(o=>{ if(o.start>=s.start+s.len) o.start+=s.len; }); const c={id:'s'+Date.now().toString(36),name:s.name.replace(/( \(copy\))*$/,'')+' (copy)',start:s.start+s.len,len:s.len};
  P.sections.push(c); WS.secSel=c.id; save(); renderSecs(); renderTL(); H.toast(`Duplicated ${s.name}, with its notes`); }
function secMove(s,dir){ const S=P.sections.slice().sort((a,b)=>a.start-b.start), i=S.indexOf(s), o=S[i+dir]; if(!o){ H.toast(dir<0?'Already the first section':'Already the last section'); return; }
  const A=dir>0?s:o, Bs=dir>0?o:s; if(A.start+A.len!==Bs.start){ H.toast('Sections must be next to each other to swap'); return; }
  wsSnap(); const B=bar(), a0=A.start*B, a1=Bs.start*B, b1=(Bs.start+Bs.len)*B;
  shiftContent((ns,t)=>ns.map(n=>{ const st=n.start-t.offset; if(st>=a0&&st<a1) return {...n,start:n.start+(b1-a1),end:n.end+(b1-a1)}; if(st>=a1&&st<b1) return {...n,start:n.start-(a1-a0),end:n.end-(a1-a0)}; return n; }));
  const as=A.start; Bs.start=as; A.start=as+Bs.len; save(); renderSecs(); renderTL(); }

// ---------- small popover + modal + export menu + settings
function pop(html,init){ closePop(); const el=document.createElement('div'); el.className='s-menu'; el.id='sPop'; el.style.top='64px'; el.style.left='50%'; el.style.right='auto'; el.style.transform='translateX(-50%)'; el.innerHTML=html; V('ws').appendChild(el); init&&init();
  setTimeout(()=>document.addEventListener('pointerdown',popAway),0); }
function popAway(e){ const el=$('sPop'); if(el&&!el.contains(e.target)) closePop(); }
function closePop(){ const el=$('sPop'); if(el) el.remove(); document.removeEventListener('pointerdown',popAway); }
function modal(title,html,narrow){ closeModal(); const m=document.createElement('div'); m.className='s-modal'; m.id='sModal';
  m.innerHTML=`<div class="box ${narrow?'narrow':''}"><div class="mh"><h2 style="margin:0">${title}</h2><button class="ghost" id="sMClose" aria-label="Close">✕</button></div><div id="sMBody">${html}</div></div>`;
  document.body.appendChild(m); m.addEventListener('pointerdown',e=>{ if(e.target===m) closeModal(); }); on('sMClose',closeModal); return m; }
let modalClose=null; function closeModal(){ const m=$('sModal'); if(modalClose){ const f=modalClose; modalClose=null; f(); } if(m) m.remove(); }
function exportMenu(){ if($('sPop')){ closePop(); return; } const t=trk(P.sel);
  pop(`<span class="lab">Whole song</span><button id="xMid">MIDI file (all tracks)</button><button id="xWav">Audio (WAV)</button>
    <hr><span class="lab">${t?esc(t.name):'Selected track'}</span><button id="xTMid" ${t?'':'disabled'}>MIDI file</button><button id="xTWav" ${t?'':'disabled'}>Audio (WAV)</button><button id="xTVoice" ${t&&t.hasAudio?'':'disabled'}>My original voice recording</button>
    <hr><button id="xScore" ${P.tracks.length?'':'disabled'}>Sheet music / PDF…</button>`,()=>{
    const el=$('sPop'); el.style.left='auto'; el.style.right='60px'; el.style.transform='none';
    on('xMid',()=>{ closePop(); saveBlob(safe(P.title)+'.mid',songMidi(P.tracks)); });
    on('xTMid',()=>{ closePop(); saveBlob(safe(P.title)+' - '+safe(t.name)+'.mid',songMidi([t])); });
    on('xWav',async()=>{ closePop(); busy('Rendering your song…'); try{ saveBlob(safe(P.title)+'.wav',await renderAudio(P.tracks)); }finally{ busy(null); } });
    on('xTWav',async()=>{ closePop(); busy('Rendering the track…'); try{ saveBlob(safe(P.title)+' - '+safe(t.name)+'.wav',await renderAudio([t])); }finally{ busy(null); } });
    on('xTVoice',async()=>{ closePop(); const b=await audioOf(t); if(b) saveBlob(safe(P.title)+' - '+safe(t.name)+' (voice).wav',H.wav(b)); else H.toast('No recording for this track'); });
    on('xScore',()=>{ closePop(); sheetMusic(t||P.tracks[0]); }); }); }
const safe=s=>String(s).replace(/[^\w\- ()]+/g,'').trim()||'song';
async function saveBlob(name,blob){ try{ const w=await H.writeFile(name,blob); if(w==='folder') H.toast(`Saved “${name}” to the recordings folder`); else if(w==='app') H.toast(`Saved “${name}” in Humnote`); }catch(e){ H.toast('Could not save'); } }
// MIDI: one file, one MIDI track per song track (type 1), with the song's tempo and time signature
function songMidi(tracks){ const PPQ=480, tps=PPQ*(P.bpm||100)/60, out=[], u32=n=>[(n>>>24)&255,(n>>>16)&255,(n>>>8)&255,n&255], u16=n=>[(n>>8)&255,n&255];
  const vlq=n=>{ n=Math.max(0,Math.round(n)); const b=[n&127]; while((n>>=7)>0) b.unshift((n&127)|128); return b; }, txt=(ty,s)=>{ const b=[...unescape(encodeURIComponent(s))].map(c=>c.charCodeAt(0)); return [0xFF,ty,...vlq(b.length),...b]; };
  const chunk=evs=>{ evs.sort((a,b)=>a[0]-b[0]||a[1]-b[1]); let last=0; const d=[]; evs.forEach(([tk,,bytes])=>{ d.push(...vlq(tk-last),...bytes); last=tk; }); d.push(0,0xFF,0x2F,0); return [...'MTrk'].map(c=>c.charCodeAt(0)).concat(u32(d.length),d); };
  const us=Math.round(60e6/(P.bpm||100)); out.push(chunk([[0,0,txt(3,P.title)],[0,0,[0xFF,0x51,3,(us>>16)&255,(us>>8)&255,us&255]],[0,0,[0xFF,0x58,4,P.ts||4,2,24,8]]]));
  let ch=0; tracks.forEach(t=>{ const I=INST[t.instrument], drums=t.instrument==='drums', c=drums?9:(ch===9?++ch:ch); if(!drums) ch=(ch+1)%16;
    const ps=t.notes.map(n=>n.pitch), lo=Math.min(...ps), hi=Math.max(...ps), drumNote=p=>{ const r=(p-lo)/Math.max(1,hi-lo); return r<0.34?36:r<0.67?38:42; };
    const ev=[[0,0,txt(3,t.name)]]; if(!drums) ev.push([0,0,[0xC0|c,I.gm]]); if(t.mute) ev.push([0,0,txt(1,'muted in Humnote')]);
    t.notes.forEach(n=>{ const s=n.start-t.offset, e=n.end-t.offset; if(e<=0) return; const p=drums?drumNote(n.pitch):Math.max(0,Math.min(127,n.pitch+(t.transpose||0))), v=Math.max(1,Math.min(127,Math.round(n.vel||90)));
      ev.push([Math.round(Math.max(0,s)*tps),2,[0x90|c,p,v]]); ev.push([Math.round(e*tps),1,[0x80|c,p,0]]); });
    out.push(chunk(ev)); });
  const head=[...'MThd'].map(c=>c.charCodeAt(0)).concat(u32(6),u16(1),u16(out.length),u16(PPQ)); return new Blob([new Uint8Array(head.concat(...out))],{type:'audio/midi'}); }
async function renderAudio(tracks){ await H.loadPiano(); const end=songEnd(), sr=44100, oc=new OfflineAudioContext(1,Math.ceil(sr*(end+1.5)),sr), bag=[], anySolo=tracks.some(t=>t.solo);
  for(const t of tracks){ if(tracks.length>1&&(t.mute||(anySolo&&!t.solo))) continue; if(t.voice) await audioOf(t); scheduleTrack(oc,t,0,end,0.02,oc.destination,bag); }
  return H.wav(await oc.startRendering()); }
// sheet music: the existing score of one track, shown on its own and printable (Save as PDF)
async function sheetMusic(t){ if(!t) return; await loadIntoEditor(t); const sc=H.$('score'), home=sc.parentElement, next=sc.nextSibling;
  const m=modal('Sheet music',`<div class="row" style="margin-bottom:12px"><select id="smTrack">${P.tracks.map(x=>`<option value="${x.id}" ${x.id===t.id?'selected':''}>${esc(x.name)}</option>`).join('')}</select><button class="pri" id="smPrint">Print / Save as PDF</button><button id="smMid">MIDI of this track</button></div><div class="score-host"></div>`);
  m.querySelector('.score-host').appendChild(sc); H.drawScore(); modalClose=()=>{ home.insertBefore(sc,next); };
  on('smTrack',async e=>{ closeModal(); sheetMusic(trk(e.target.value)); },'change'); on('smMid',()=>saveBlob(safe(P.title)+' - '+safe(t.name)+'.mid',songMidi([t])));
  on('smPrint',()=>{ document.body.classList.add('printing'); window.print(); setTimeout(()=>document.body.classList.remove('printing'),500); }); }
function settings(){ const m=modal('Settings','<div id="setHost" style="display:flex;flex-direction:column;gap:14px"></div><hr style="border:0;border-top:1px solid #262a45;margin:18px 0"><div class="row"><button id="setClassic">Open the classic full view</button><span class="small">Every detection setting, the note list and the old controls.</span></div>',true);
  const host=m.querySelector('#setHost'); const a=H.$('setup').querySelector('.menuBody'), b=H.$('liveMenu').querySelector('.menuBody'), homeA=H.$('setup'), homeB=H.$('liveMenu');
  [a,b].forEach(x=>{ x.style.position='static'; x.style.width='auto'; x.style.boxShadow='none'; x.style.border='0'; x.style.padding='0'; x.style.background='transparent'; host.appendChild(x); });
  modalClose=()=>{ [a,b].forEach(x=>x.removeAttribute('style')); homeA.appendChild(a); homeB.appendChild(b); };
  on('setClassic',()=>{ closeModal(); classic(true); }); }
function classic(onn){ if(onn){ document.body.classList.remove('studio-on'); window.HN_block=false; let b=$('sBackStudio'); if(!b){ b=document.createElement('button'); b.id='sBackStudio'; b.textContent='← Back to Humnote Studio'; b.className='primary'; b.style.cssText='position:fixed;right:16px;bottom:16px;z-index:60'; b.onclick=()=>classic(false); document.body.appendChild(b); } b.hidden=false; }
  else { document.body.classList.add('studio-on'); window.HN_block=true; const b=$('sBackStudio'); if(b) b.hidden=true; H.stopPlay(); } }

// ---------- full-screen track editor = the existing note editor, loaded with this track
const ED={t:null,from:'ws'};
const edBar=document.createElement('div'); edBar.className='ed-bar'; edBar.id='edBar';
edBar.innerHTML=`<button id="edBack">← Back to the song</button><span class="sw" id="edSw"></span><b id="edName"></b><select id="edInst" aria-label="Instrument">${Object.entries(INST).map(([k,v])=>`<option value="${k}">${v.name}</option>`).join('')}</select><span style="flex:1"></span><span style="font-size:13px;color:#8d8fa8">Drag notes to move · drag their ends to resize · double-click to add · Delete removes · Ctrl+C / Ctrl+V copy · select notes to change velocity</span>`;
document.body.prepend(edBar);
async function loadIntoEditor(t){ const st=H.st; let buf=await audioOf(t);
  if(!buf){ const sr=16000, len=Math.max(4,Math.max(...t.notes.map(n=>n.end),0)+2); buf=H.ac().createBuffer(1,Math.ceil(sr*len),sr); }
  let A=ANA.get(t.id); if(!A){ busy('Opening the editor…'); try{ const x=await H.toMono16k(buf); A={F:await H.analyze(x,16000)}; ANA.set(t.id,A); }finally{ busy(null); } }
  H.stopPlay(); st.buf=buf; st.F=A.F; st.demo=false; st.loop=null; st.sel=-1; H.undo.length=0; H.clearSel(); H.redecode(true);   // tuning + key from the voice
  const b=beat(); st.notes=cloneNotes(t.notes); st.edited=true; st.tr=t.transpose||0; st.snd=INST[t.instrument].snd; drumRange(t);
  st.tempo={bpm:P.bpm||100,beat:b,phase:((t.offset%b)+b)%b,down:t.offset,ts:P.ts||4,conf:1}; st.ts=P.ts||4; st.tsAuto=false;
  if(P.key) st.res.key={...(st.res.key||{}),tonic:P.key.tonic,mode:P.key.mode,scale:H.keyPcs(P.key),name:H.Hum.FLATS[P.key.tonic]+' '+P.key.mode,conf:1};   // the song's key, not a fresh guess
  H.render(); H.showLoop(); }
async function openEditor(t,from){ if(!t) return; stopSong(); ED.prevSnd=H.st.snd; await loadIntoEditor(t); ED.t=t; ED.from=from||'ws';
  $('edSw').style.background=INST[t.instrument].color; $('edName').textContent=t.name; $('edInst').value=t.instrument;
  WS.scroll=$('wsMain')?[$('wsMain').scrollLeft,$('wsMain').scrollTop]:null;
  document.body.classList.add('editor-on'); window.HN_block=false; window.scrollTo(0,0); H.setPos(Math.max(0,(ED.from==='ws'?WS.pos:0)+t.offset)); }
function closeEditor(){ const t=ED.t; if(t){ t.notes=cloneNotes(H.st.notes); t.base=cloneNotes(t.notes); t.q=null; save(); }
  H.stopPlay(); H.st.tr=0; if(ED.prevSnd) H.st.snd=ED.prevSnd; ED.t=null; document.body.classList.remove('editor-on'); window.HN_block=true;
  if(ED.from==='ws'&&cur==='ws'){ renderTL(); renderBottom(); if(WS.scroll){ $('wsMain').scrollLeft=WS.scroll[0]; $('wsMain').scrollTop=WS.scroll[1]; } } else go(ED.from==='review'?'review':cur); }
on('edBack',closeEditor);
on('edInst',e=>{ const t=ED.t; if(!t) return; const k=e.target.value, was=INST[t.instrument]; if(t.transpose===was.tr) t.transpose=INST[k].tr; t.instrument=k; H.st.snd=INST[k].snd; H.st.tr=t.transpose||0; drumRange(t); $('edSw').style.background=INST[k].color; save(); H.render(); },'change');

let rzT=0; window.addEventListener('resize',()=>{ clearTimeout(rzT); rzT=setTimeout(()=>{ if(cur==='review'){ const t=trk(REV.id); if(t&&!SP.on) drawMini($('sRvCv'),[t]); } else if(cur==='ws') renderTL(); },120); });
// ---------- keyboard: T (tempo), space (tap / play), K (key mic), Esc
window.addEventListener('keydown',e=>{ if(!document.body.classList.contains('studio-on')||document.body.classList.contains('editor-on')) return;
  const tag=(e.target.tagName||'').toLowerCase(); if(tag==='input'||tag==='textarea'||tag==='select') return; if(e.ctrlKey||e.metaKey||e.altKey) return;
  if(cur==='tempo'&&(e.key==='t'||e.key==='T')){ e.preventDefault(); tToggle(); }
  else if(cur==='tempo'&&e.key===' '){ e.preventDefault(); tapBeat(); }
  else if(cur==='key'&&KY.tab==='sing'&&(e.key==='k'||e.key==='K')){ e.preventDefault(); kToggle(); }
  else if(cur==='ws'&&e.key===' '){ e.preventDefault(); wsToggle(); }
  else if(cur==='review'&&e.key===' '){ e.preventDefault(); $('sRvPlay')&&$('sRvPlay').click(); }
  else if(e.key==='Escape'){ closePop(); closeModal(); } },true);

// ---------- developer / testing panel (hidden: add ?dev to the address, or press Ctrl+Shift+D)
let DEV=false; try{ DEV=new URLSearchParams(location.search).has('dev')||localStorage.getItem('humnote_dev')==='1'; }catch(e){}
const dev=document.createElement('div'); dev.className='s-dev'; dev.hidden=true; document.body.appendChild(dev);
function devRender(){ dev.hidden=!DEV; if(!DEV) return; const open=dev.dataset.open==='1';
  dev.innerHTML=`<button id="dvT">DEV ${open?'▾':'▸'}</button>${open?`<div class="p">
    <b>JUMP TO A STEP</b><div class="g">${[['start','Start'],['tempo','1 Tempo'],['key','2 Key'],['inst','3 Instrument'],['rec','4 Record'],['review','5 Review'],['done','Track done'],['ws','Workspace']].map(([v,l])=>`<button data-dv="${v}">${l}</button>`).join('')}<button id="dvEd">Editor (sel. track)</button></div>
    <b>RESET</b><div class="g"><button id="dvRS">Reset this step</button><button id="dvRA">Reset whole walkthrough</button></div>
    <b>TEST DATA (always labelled on screen)</b><div class="g"><button id="dvSong">Load sample song (3 tracks)</button><button id="dvTake">Real analysis of the sample voice → new track</button><button id="dvBpm">Simulated tempo 96</button><button id="dvKey">Simulated key C major</button><button id="dvCh">Example chords (capo 4)</button><button id="dvQ">Quantize test</button></div>
    <b>NOW</b><div id="dvInfo" style="color:#d6c38a;line-height:1.5"></div>
    <div class="g"><button id="dvOff">Hide dev mode</button></div></div>`:''}`;
  $('dvT').onclick=()=>{ dev.dataset.open=open?'0':'1'; devRender(); }; if(!open) return;
  dev.querySelectorAll('[data-dv]').forEach(b=>b.onclick=()=>{ if(document.body.classList.contains('editor-on')) closeEditor(); if(b.dataset.dv==='review'&&!trk(REV.id||P.sel)) { H.toast('No track yet: load the sample song first'); return; } go(b.dataset.dv); });
  on('dvEd',()=>{ const t=trk(P.sel)||P.tracks[0]; if(t) openEditor(t,'ws'); else H.toast('No track yet'); });
  on('dvRS',devResetStep); on('dvRA',()=>{ if(!confirm('Reset the whole walkthrough and song?')) return; resetAll(); go('start'); });
  on('dvSong',loadSample); on('dvTake',devTake);
  on('dvBpm',()=>{ setBpm(96,'sim'); go('tempo'); }); on('dvKey',()=>{ KY.tab='sing'; KY.res=[{tonic:0,mode:'major'},{tonic:9,mode:'minor'},{tonic:7,mode:'major'}]; KY.src='sim'; KY.sel=0; KY.mid=60; setKeyP(KY.res[0],'sim'); go('key'); });
  on('dvCh',()=>{ KY.tab='chords'; P.chordInst='guitar'; P.capo=4; P.chords=[{root:0,q:''},{root:7,q:''},{root:9,q:'m'},{root:5,q:''}]; save(); go('key'); });
  on('dvQ',async()=>{ if(!P.tracks.length) await loadSample(); REV.id=P.tracks[0].id; REV.hist=[]; go('review'); });
  on('dvOff',()=>{ DEV=false; try{ localStorage.setItem('humnote_dev','0'); }catch(e){} devRender(); });
  devInfo(); }
function devInfo(){ const el=$('dvInfo'); if(!el) return; const tests=P.tracks.filter(t=>t.test).length;
  el.innerHTML=`view: ${cur}<br>tempo: ${P.bpm??'—'} BPM (${P.bpmSrc||'—'}), ${P.ts}/4<br>key: ${keyLabel(P.key)} (${P.keySrc||'—'})<br>chords: ${P.chords.map(chName).join(' ')||'—'} capo ${P.capo}<br>tracks: ${P.tracks.length}${tests?` (${tests} test)`:''} · sections: ${P.sections.length}<br>live engine: ${H.liveOK?'native (Windows app)':'in-page'}`; }
function devResetStep(){ if(cur==='tempo'){ P.bpm=null; P.bpmSrc=null; TP.tap=[]; } else if(cur==='key'){ P.key=null; P.keySrc=null; KY.res=null; P.chords=[]; P.capo=0; } else if(cur==='inst'){ P.nextInst='piano'; }
  else if(cur==='review'){ const t=trk(REV.id); if(t){ t.notes=cloneNotes(t.base); t.q=null; REV.hist=[]; } } else if(cur==='ws'){ WS.pos=0; WS.secSel=null; } save(); go(cur); }
window.addEventListener('keydown',e=>{ if(e.ctrlKey&&e.shiftKey&&(e.key==='D'||e.key==='d')){ e.preventDefault(); DEV=!DEV; try{ localStorage.setItem('humnote_dev',DEV?'1':'0'); }catch(_){} dev.dataset.open='1'; devRender(); } },true);
// sample song: the built-in sample voice really analysed (TEST audio), plus a generated bass line and drum beat (TEST, generated)
async function loadSample(){ busy('Analysing the sample voice (test audio)…');
  try{ await H.run(H.demoBuffer(),true); const st=H.st, T=st.tempo; P.bpm=Math.round(T.bpm); P.bpmSrc='sim'; P.ts=T.ts||st.ts||3; P.key=st.res.key?{tonic:st.res.key.tonic,mode:st.res.key.mode}:{tonic:0,mode:'major'}; P.keySrc='sim'; P.title='Sample song (test)';
    const B=60/P.bpm*P.ts, id=k=>'t'+Date.now().toString(36)+k, prog=[0,7,7,0,0,5,0,7,0];
    const mel={id:id('a'),name:'Keys (sample voice)',instrument:'piano',notes:cloneNotes(st.notes),base:cloneNotes(st.notes),q:null,offset:T.down,vol:0.8,mute:false,solo:false,transpose:0,voice:false,hasAudio:true,test:true,created:Date.now()};
    AUD.set(mel.id,st.buf); ANA.set(mel.id,{F:st.F}); try{ await H.kv('studio:audio:'+mel.id,H.wav(st.buf)); }catch(e){}
    const bass={id:id('b'),name:'Bass (generated)',instrument:'bass',notes:prog.map((r,i)=>({start:i*B,end:(i+1)*B-0.05,pitch:48+r,vel:92,cents:0,rel:0})),q:null,offset:0,vol:0.75,mute:false,solo:false,transpose:-12,voice:false,hasAudio:false,test:true,created:Date.now()}; bass.base=cloneNotes(bass.notes);
    const dn=[]; for(let b=0;b<prog.length*P.ts;b++){ const t=b*60/P.bpm; dn.push({start:t,end:t+0.1,pitch:b%P.ts===0?40:b%P.ts===P.ts-1?50:60,vel:b%P.ts===0?110:85,cents:0,rel:0}); }
    const drums={id:id('c'),name:'Drums (generated)',instrument:'drums',notes:dn,base:clone(dn),q:null,offset:0,vol:0.7,mute:false,solo:false,transpose:0,voice:false,hasAudio:false,test:true,created:Date.now()};
    P.tracks=[mel,bass,drums]; P.sections=[{id:'s1',name:'Verse 1',start:0,len:4},{id:'s2',name:'Chorus 1',start:4,len:5}]; P.sel=mel.id; REV.id=mel.id; save(); H.toast('Sample song loaded (test data)');
    if(cur==='ws') vWS(); }
  finally{ busy(null); } }
async function devTake(){ busy('Analysing the sample voice…'); try{ await H.run(H.demoBuffer(),true); const st=H.st, id='t'+Date.now().toString(36);
    const t={id,name:'Sample voice take',instrument:P.nextInst||'piano',notes:cloneNotes(st.notes),base:cloneNotes(st.notes),q:null,offset:st.tempo?st.tempo.down:0,vol:0.8,mute:false,solo:false,transpose:0,voice:false,hasAudio:true,test:true,created:Date.now()};
    if(!P.bpm){ P.bpm=Math.round(st.tempo.bpm); P.bpmSrc='sim'; } AUD.set(id,st.buf); ANA.set(id,{F:st.F}); try{ await H.kv('studio:audio:'+id,H.wav(st.buf)); }catch(e){}
    P.tracks.push(t); P.sel=id; REV.id=id; REV.hist=[]; save(); go('review'); } finally{ busy(null); } }

// ---------- start: reopen the song where you left it
(async()=>{ await loadProject(); if(P.key) H.setKey(P.key); devRender(); const v=P.view==='rec'||P.view==='review'&&!trk(P.sel)?(P.tracks.length?'ws':'inst'):P.view; if(P.view==='review') REV.id=P.sel; go(v||'start'); })();
})();
