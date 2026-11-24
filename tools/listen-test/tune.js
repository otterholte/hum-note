// The tuner: loads every test clip once, then tries settings for the app's note decisions (Hum.HP) and keeps
// whatever raises the average score over the tuning sets. Held-back sets are only reported, never tuned on.
// usage: node tune.js <index.html> [rounds=2] [out.json]
const fs=require('fs'), path=require('path'), D=__dirname; const [,,html,roundsArg='2',outf=path.join(D,'tuned.json')]=process.argv;
const Hum=new Function(fs.readFileSync(html,'utf8').match(/<script id="core">([\s\S]*?)<\/script>/)[1]+';return Hum;')();
function wav(f){ const b=fs.readFileSync(f); let o=12,sr=0,ch=1,bits=16,data; while(o<b.length-8){ const id=b.toString('ascii',o,o+4),L=b.readUInt32LE(o+4); if(id==='fmt '){ch=b.readUInt16LE(o+10);sr=b.readUInt32LE(o+12);bits=b.readUInt16LE(o+22);} if(id==='data')data=b.subarray(o+8,o+8+L); o+=8+L+(L&1); }
  const n=data.length/(bits/8)/ch, x=new Float32Array(n); for(let i=0;i<n;i++){ let s=0; for(let c=0;c<ch;c++) s+=bits===16?data.readInt16LE((i*ch+c)*2)/32768:data.readFloatLE((i*ch+c)*4); x[i]=s/ch; }
  const r=sr/16000, N=Math.floor(n/r), y=new Float32Array(N); for(let i=0;i<N;i++){ let s=0,c=0; for(let k=Math.floor(i*r);k<Math.floor((i+1)*r);k++){ s+=x[k]; c++; } y[i]=s/c; }
  let pk=0; for(const v of y) pk=Math.max(pk,Math.abs(v)); for(let i=0;i<N;i++) y[i]*=0.9/pk; return y; }
function prep(f,swdir){ const tr=Hum.track(wav(f),16000), sp=path.join(swdir,path.basename(f).replace(/\.wav$/,'.json')); if(fs.existsSync(sp)){ const sw=JSON.parse(fs.readFileSync(sp,'utf8')); Hum.useSwift(tr,sw,Hum.swiftMask(tr,sw)); } return Hum.frames(tr); }
function transcribe(F){ const opt={keyStrength:1,keyMode:'on',switchCost:10}; const tune=Hum.tuningCurve(F); let notes=Hum.decode(F,tune,null,opt), key=null;
  if(notes.length>=3){ key=Hum.detectKey(notes); notes=Hum.decode(F,tune,key,opt); key=Hum.detectKey(notes); }
  if(notes.length>=4) Hum.refine(F,tune,notes); notes=Hum.decode(F,tune,key,{...opt,shape:1});
  if(key){ const k2=Hum.driftKey(notes)||key; Hum.applyDrift(F,tune,Hum.followDrift(Hum.decode(F,tune,k2,{...opt,shape:1}),k2)); key=Hum.recenter(tune,k2); notes=Hum.decode(F,tune,key,{...opt,shape:1}); }
  return notes.map(o=>o.pitch); }
function ed(a,b){ const D=[...Array(a.length+1)].map(()=>new Int16Array(b.length+1)); for(let i=0;i<=a.length;i++) D[i][0]=i; for(let j=0;j<=b.length;j++) D[0][j]=j;
  for(let i=1;i<=a.length;i++) for(let j=1;j<=b.length;j++) D[i][j]=Math.min(D[i-1][j]+1,D[i][j-1]+1,D[i-1][j-1]+(a[i-1]===b[j-1]?0:1)); return D; }
const prefixScore=(got,ref)=>{ let best=-1; for(let sh=-30;sh<=30;sh++){ const r=ref.map(p=>p+sh), M=ed(got,r); for(let j=Math.max(3,Math.floor(got.length*0.5));j<=r.length;j++) best=Math.max(best,1-M[got.length][j]/j); } return Math.max(0,best); };
const fullScore=(got,ref)=>{ let best=-1; for(let sh=-24;sh<=24;sh++){ const r=ref.map(p=>p+sh); best=Math.max(best,1-ed(got,r)[got.length][r.length]/r.length); } return Math.max(0,best); };
const NM=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'], midi=s=>{ const m=s.match(/^([A-G]b?)(-?\d)$/); return NM.indexOf(m[1])+12*(+m[2]+1); };
const KEY="C3 D3 E3 D3 C3 D3 C3 A2 C3 C3 D3 E3 D3 C3 D3 C3 A2 D3 C3 D3 E3 G3 D3 E3 D3 C3 A2 C3 E3 F3 F3 E3".split(' ').map(midi);
const SETS={bench:'prefix',clips:'prefix',ht:'full',csd:'full',voc:'full'}, HOLD={htx:'full',csdx:'full',vocx:'full'}; const data={};
const t0=Date.now();
for(const s of [...Object.keys(SETS),...Object.keys(HOLD)]){ const idx=JSON.parse(fs.readFileSync(path.join(D,s,'index.json'),'utf8')); data[s]=[];
  for(const [k,c] of Object.entries(idx)){ if(!c.ref) continue; const f=path.join(D,s,k+'.wav'); if(!fs.existsSync(f)) continue; data[s].push({ref:c.ref,F:prep(f,path.join(D,s+'_swift'))}); } }
const take=prep(path.join(D,'..','..','recordings','hum_2026-11-24_015826.wav'),path.join(D,'..','pitch-compare','take_swift'));
console.log('loaded in',((Date.now()-t0)/1000).toFixed(0),'s:',Object.entries(data).map(([k,v])=>k+' '+v.length).join(', '));
function evalAll(P,withHold){ Object.assign(Hum.HP,P); const r={};
  for(const [s,kind] of Object.entries(withHold?{...SETS,...HOLD}:SETS)){ let t=0; for(const c of data[s]){ const g=transcribe(c.F); t+=kind==='prefix'?prefixScore(g,c.ref):fullScore(g,c.ref); } r[s]=100*t/data[s].length; }
  const g=transcribe(take); r.take=ed(g,KEY)[g.length][KEY.length]; r.obj=Object.keys(SETS).reduce((a,s)=>a+r[s],0)/Object.keys(SETS).length-0.5*Math.max(0,r.take-2); return r; }
const fmt=r=>Object.entries(r).map(([k,v])=>k+' '+(k==='take'?v:v.toFixed(1))).join(' | ');
if(process.env.EVAL){ const S={...Hum.HP,...(process.env.START?JSON.parse(fs.readFileSync(process.env.START,'utf8')):{})}; for(const e of process.env.EVAL.split(';')) console.log(e.padEnd(40),fmt(evalAll({...S,...JSON.parse(e)},true))); process.exit(0); }
let P={...Hum.HP,...(process.env.START?JSON.parse(fs.readFileSync(process.env.START,'utf8')):{})}; const base=evalAll(P,true); console.log('start  ',fmt(base)); let best=base.obj;
const steps={onMode:[1,2,3],onTh:[0.3,0.4,0.6,0.7],onAdd:[0.8,0.85,0.95],sigma:[0.25,0.3,0.38,0.45],kappa:[0.6,0.9,1.6,2],TN:[6,8,13,16],TS:[2,3,6],gapF:[4,5,8,10],gapDip:[2,3,6],dip:[3,4,6,7,9],nvTh:[4,4.5,6,7],nvDip:[0,0.3,1,2],tailS:[0.1,0.2,0.25],tailDB:[1.5,2,4,6],veto:[1.5,2,3,3.5,4.5],
  minF:[0.04,0.08,0.1],shortF:[0.12,0.2,0.25],glideSlope:[0.025,0.05,0.07],glideStab:[0.3,0.6],scoopS:[0.1,0.12,0.18,0.22],scoopST:[1,3],scoopR:[1,2,3],foldL:[0.2,0.25,0.4],foldSet:[0.03,0.1,0.15],nbFlat:[0.5,0.6,0.8,0.9]};
for(let round=0;round<+roundsArg;round++){ for(const [k,vals] of Object.entries(steps)){ for(const v of vals){ const Q={...P,[k]:v}; const r=evalAll(Q,false);
      if(r.obj>best+0.05){ best=r.obj; P=Q; console.log(`round ${round+1}: ${k}=${v} -> ${fmt(r)}`); fs.writeFileSync(outf,JSON.stringify(P,null,1)); } } } }
const fin=evalAll(P,true); console.log('final  ',fmt(fin)); console.log('changed',JSON.stringify(Object.fromEntries(Object.entries(P).filter(([k,v])=>base&&v!==Hum.HP[k]&&false)))); fs.writeFileSync(outf,JSON.stringify(P,null,1));
console.log('settings',JSON.stringify(P)); console.log('took',((Date.now()-t0)/60000).toFixed(1),'min');
