// Runs the page's detection core on a WAV file, outside the browser.
// usage: node tools/run.js recordings/take.wav [from to]   (prints notes, and pitch frames in [from,to] s)
const fs=require('fs'), path=require('path'), vm=require('vm');
const html=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8');
const core=html.match(/<script id="core">([\s\S]*?)<\/script>/)[1];
const Hum=require('./dbg.js');
function readWav(f){ const b=fs.readFileSync(f); let o=12, sr=0, ch=1, bits=16, data=null;
  while(o<b.length-8){ const id=b.toString('ascii',o,o+4), L=b.readUInt32LE(o+4);
    if(id==='fmt '){ ch=b.readUInt16LE(o+10); sr=b.readUInt32LE(o+12); bits=b.readUInt16LE(o+22); }
    if(id==='data') data=b.subarray(o+8,o+8+L); o+=8+L+(L&1); }
  const n=data.length/(bits/8)/ch, x=new Float32Array(n);
  for(let i=0;i<n;i++){ let s=0; for(let c=0;c<ch;c++) s+= bits===16? data.readInt16LE((i*ch+c)*2)/32768 : data.readFloatLE((i*ch+c)*4); x[i]=s/ch; }
  return {x,sr}; }
function resample(x,sr,to){ if(sr===to) return x; const r=to/sr, n=Math.ceil(x.length*r), y=new Float32Array(n), fc=Math.min(1,r)*0.95, Z=16;
  for(let i=0;i<n;i++){ const t=i/r, c=Math.floor(t); let s=0,w=0; for(let k=c-Z/fc|0;k<=c+Z/fc;k++){ if(k<0||k>=x.length) continue; const u=(t-k)*fc, sinc=u===0?1:Math.sin(Math.PI*u)/(Math.PI*u), win=0.5+0.5*Math.cos(Math.PI*Math.min(1,Math.abs(t-k)*fc/Z)); const g=sinc*win; s+=x[k]*g; w+=g; } y[i]=w?s/w:0; }
  return y; }
const [,,file,from,to]=process.argv; const {x,sr}=readWav(file); const y=resample(x,sr,16000);
let pk=0; for(const v of y) pk=Math.max(pk,Math.abs(v)); for(let i=0;i<y.length;i++) y[i]*=0.9/pk;
const opt={keyStrength:1,keyMode:'on',switchCost:10};
const r=Hum.transcribe(y,16000,opt); const F=r.frames;
console.log('key',r.key&&r.key.name,'tune0',Math.round(100*r.tuning.curve[0]));
r.notes.forEach((n,i)=>console.log(String(i).padStart(2),Hum.flatName(n.pitch).padEnd(4),n.start.toFixed(2),n.end.toFixed(2),'rel',n.rel,n.why||''));
if(from){ for(let i=0;i<F.n;i++){ const t=F.t0+i*F.dt; if(t<+from||t>+to) continue; const rel=F.voiced[i]?(F.m[i]-r.tuning.curve[i]):NaN;
  console.log(t.toFixed(2), F.voiced[i]?Hum.flatName(Math.round(rel)).padEnd(4)+(rel).toFixed(2):'  -   ', F.ds[i].toFixed(0)); } }
