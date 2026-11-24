// Tests tempo, meter (3/4 vs 4/4) and where bar 1 starts, on:
//   csd   100 sung children's songs (note times from the hand-aligned MIDI; bar lines known exactly)
//   tunes 6 well-known tunes x 8 renditions with human timing wobble (meter, pickup and chords known)
//   take  the app's own transcription of 50 CSD clips (the real pipeline, mistakes and all)
// usage: node meter_eval.js <index.html> [--list]
const fs=require('fs'), path=require('path'), D=__dirname; const html=process.argv[2]||path.join(D,'..','..','index.html'), list=process.argv.includes('--list');
const Hum=new Function(fs.readFileSync(html,'utf8').match(/<script id="core">([\s\S]*?)<\/script>/)[1]+';return Hum;')();
const TUNES=require('./tunes.js'); const MF=process.env.PROTO?require('./meterfn.js'):null, WJ=process.env.W?JSON.parse(process.env.W):{};
let seed=11; const rnd=()=>(seed=(seed*1664525+1013904223)>>>0)/4294967296, gauss=()=>{ let u=0; for(let i=0;i<6;i++) u+=rnd(); return (u-3)/Math.sqrt(0.5); };
function perform(T){ const bpm=70+rnd()*70, beat=60/bpm, drift=(rnd()-0.5)*0.12, t0=0.3+rnd()*0.6, notes=[]; let b=0;
  const time=bb=>t0+bb*beat*(1+drift*bb/40); // a singer who slowly speeds up or slows down
  for(const [p,len] of T.notes){ const s=time(b)+gauss()*0.025, e=time(b+len)-0.05-rnd()*0.05; notes.push({start:s,end:Math.max(s+0.06,e),pitch:p}); b+=len; }
  return {notes,beat,meter:T.meter,down:time(T.pickup),bpm}; }
const items=[];
const csd=JSON.parse(fs.readFileSync(path.join(D,'meter_csd.json'),'utf8'));
for(const [k,c] of Object.entries(csd)){ if(c.meter===2) continue; items.push({set:'csd',name:k,notes:c.notes.map(([s,e,p])=>({start:s,end:e,pitch:p})),beat:c.beat,meter:c.meter,down:0}); }
for(const [k,T] of Object.entries(TUNES)) for(let r=0;r<8;r++){ const P=perform(T); items.push({set:'tunes',name:k+' #'+(r+1),notes:P.notes,beat:P.beat,meter:P.meter,down:P.down,tune:k}); }
for(const s of ['csd','csdx']){ const idx=JSON.parse(fs.readFileSync(path.join(D,s,'index.json'),'utf8'));
  for(const [k,c] of Object.entries(idx)){ const f=path.join(D,'out_'+s,k+'.json'), m=csd[k]; if(!fs.existsSync(f)||!m||m.meter===2) continue;
    const t0=m.notes.find(n=>Math.abs(n[2]-c.ref[0])<1&&n[0]>=0)[0]-c.times[0][0]; const J=JSON.parse(fs.readFileSync(f,'utf8'));
    items.push({set:'take',name:k,notes:J.notes.map(n=>({start:n.start,end:n.end,pitch:n.pitch})),beat:m.beat,meter:m.meter,down:-t0}); } }
const R={}; const rows=[]; let TOT=0;
for(const it of items){ const tp=Hum.tempo(it.notes); const g=R[it.set]=R[it.set]||{n:0,tempo:0,half:0,dbl:0,meter:0,down:0};
  g.n++; if(!tp){ rows.push(`${it.set} ${it.name}: no tempo`); continue; }
  const M0=MF?MF(it.notes,tp,WJ):Hum.meter?Hum.meter(it.notes,tp):{beat:tp.beat}; const ratio=(M0.beat||tp.beat)/it.beat, ok=Math.abs(ratio-1)<0.06; if(ok) g.tempo++; else if(Math.abs(ratio-2)<0.12) g.half++; else if(Math.abs(ratio-0.5)<0.03) g.dbl++;
  const M=MF?MF(it.notes,tp,WJ):Hum.meter?Hum.meter(it.notes,tp):{ts:4,down:tp.phase,beat:tp.beat};
  const mOK=M.ts===it.meter; if(ok&&mOK) g.meter++;
  // a detected downbeat is right if it lands on a true downbeat (within a quarter beat)
  const bar=it.beat*it.meter, d=((M.down-it.down)/bar%1+1)%1, dOK=ok&&mOK&&Math.min(d,1-d)*it.meter<0.25; if(dOK) g.down++;
  rows.push(`${it.set.padEnd(5)} ${it.name.padEnd(28)} tempo ${ok?'ok':(ratio).toFixed(2)}  meter ${M.ts}/${it.meter} ${mOK?'ok':'X'}  bar1 ${dOK?'ok':'X'}`); }
if(list) console.log(rows.join('\n'));
for(const [k,g] of Object.entries(R)){ TOT+=g.down/g.n; console.log(`${k.padEnd(6)} n=${g.n}  tempo right ${(100*g.tempo/g.n).toFixed(0)}% (half-speed ${g.half}, double ${g.dbl})  meter right ${(100*g.meter/g.n).toFixed(0)}%  bar lines right ${(100*g.down/g.n).toFixed(0)}%`); }
console.log('average bar lines right', (100*TOT/Object.keys(R).length).toFixed(1));
// SEARCH=1: try other cue weights (coordinate search) and keep whatever gets more bar lines right on average
if(process.env.SEARCH&&MF){ const score=W=>{ const G={}; for(const it of items){ const tp=Hum.tempo(it.notes); const g=G[it.set]=G[it.set]||{n:0,d:0}; g.n++; if(!tp) continue;
      const M=MF(it.notes,tp,W); if(Math.abs(M.beat/it.beat-1)>=0.06||M.ts!==it.meter) continue; const bar=it.beat*it.meter, d=((M.down-it.down)/bar%1+1)%1; if(Math.min(d,1-d)*it.meter<0.25) g.d++; }
    const v=Object.values(G).map(g=>g.d/g.n); return 100*v.reduce((a,b)=>a+b)/v.length; };
  let W={R:0.5,S:2,H:2,C:9,bpm:1.6,m4:0.075,dbl:0,P:0.5,Sm:1,Hm:0,...WJ}, best=score(W); console.log('start',best.toFixed(1));
  for(let round=0;round<3;round++) for(const k of Object.keys(W)) for(const f of [0,0.5,0.75,1.33,2,3]){ const T={...W,[k]:f===0?0:W[k]*f||f}; const s=score(T); if(s>best+0.2){ best=s; W=T; console.log(round,k,'=',+T[k].toFixed(3),'->',s.toFixed(1)); } }
  console.log('best',JSON.stringify(W)); }
