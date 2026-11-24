// Checks the warm-up's syllable counter on generated singing: the tail of a high note, then "da" x N on the first note.
const fs=require('fs'); const H=fs.readFileSync(__dirname+'/../index.html','utf8');
const Hum=new Function(H.match(/<script id="core">([\s\S]*?)<\/script>/)[1]+';return Hum;')();
const W=fs.readFileSync(__dirname+'/warmup.js','utf8'); const fn=W.slice(W.indexOf('function wuSyllables'),W.indexOf('function wuDone'));
const wuSyllables=new Function(fn+';return wuSyllables;')();
function sing(parts,sr=16000){ const out=[]; let ph=0; for(const [m,dur,env] of parts){ const f=m?440*2**((m-69)/12):0, n=Math.round(dur*sr);
  for(let i=0;i<n;i++){ const t=i/sr; ph+=2*Math.PI*f/sr; let a=m?(env?env(t,dur):0.3):0; let v=0; for(let k=1;k<=8;k++) v+=Math.sin(k*ph)/k; out.push(a*v*0.5+(Math.random()-0.5)*0.002); } } return Float32Array.from(out); }
const da=(per,dip)=>(t)=>{ const ph=t%per; return ph<0.07?0.3*dip+0.3*(1-dip)*(ph/0.07):ph>per-0.12?0.3*dip:0.3; };
for(const [n,per,dip,lab] of [[4,0.8,0.08,'crisp d'],[4,0.6,0.35,'soft d'],[4,0.9,0.7,'very legato'],[6,0.45,0.1,'fast crisp']]){
  const x=sing([[67,1.2],[0,0.2],[60,n*per,da(per,dip)],[0,0.3]]); const F=Hum.frames(Hum.track(x,16000)); const r=wuSyllables(F,60);
  console.log(`${lab.padEnd(12)} sang ${n}: heard ${r.n}, level rise ${r.rise.toFixed(1)} dB`); }
