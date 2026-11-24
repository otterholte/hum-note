// Synthetic singer tests: each case lists the notes a listener would write down.
const Hum=require('./dbg.js');
function sing(segs,{sr=16000,vibHz=5.5,detune=-0.3}={}){ // segs: [pitch,dur,{vib,turn,gap}]
  const total=segs.reduce((s,g)=>s+g[1]+(g[2]?.gap??0.05),0)+0.6, x=new Float32Array(Math.ceil(total*sr)); let t=0.3,ph=0,R=(s=>()=>(s=(s*1664525+1013904223)>>>0)/4294967296)(3);
  for(const [p,d,o={}] of segs){ const s0=Math.floor(t*sr), s1=Math.floor((t+d)*sr);
    for(let s=s0;s<s1;s++){ const tt=(s-s0)/sr; let m=p+detune-0.4*Math.exp(-tt/0.03);
      if(o.vib) m+=o.vib*Math.sin(2*Math.PI*vibHz*Math.max(0,tt-0.12))*Math.min(1,Math.max(0,tt-0.12)/0.1);
      if(o.turn){ const [tc,amt,w]=o.turn; const u=(tt-tc)/w; if(Math.abs(u)<1) m+=amt*(0.5+0.5*Math.cos(Math.PI*u)); }
      const f=440*2**((m-69)/12); ph+=2*Math.PI*f/sr; const env=Math.min(1,tt/0.02,(d-tt)/0.03);
      let v=0; for(let k=1;k*f<4000;k++) v+=Math.sin(k*ph)*(1+2*Math.exp(-(((k*f-700)/250)**2)))/k; x[s]+=0.1*env*v+(R()*2-1)*0.003; }
    t+=d+(o.gap??0.05); }
  return x; }
const cases=[
 ['held note, ±1.2 st vibrato', [[60,1.6,{vib:1.2}]], 'C4'],
 ['held note, ±1.8 st operatic vibrato', [[60,1.6,{vib:1.8}]], 'C4'],
 ['held D with one quick turn up to E', [[62,0.9,{turn:[0.45,2,0.08]}]], 'D4 E4 D4'],
 ['held D, small vibrato, quick turn up to E', [[62,1.2,{vib:0.3,turn:[0.6,2,0.08]}]], 'D4 E4 D4'],
 ['fast run C D E F G (0.12s each, legato)', [[60,.12,{gap:0}],[62,.12,{gap:0}],[64,.12,{gap:0}],[65,.12,{gap:0}],[67,.4]], 'C4 D4 E4 F4 G4'],
 ['repeated notes on syllables', [[64,.3],[64,.3],[64,.3],[62,.5]], 'E4 E4 E4 D4'],
 ['higher voice melody w/ vibrato', [[72,.4],[74,.4],[76,.8,{vib:0.6}],[74,.4],[72,1,{vib:0.7}]], 'C5 D5 E5 D5 C5'],
];
let pass=0; for(const [name,segs,want] of cases){ const r=Hum.transcribe(sing(segs),16000,{keyStrength:1,switchCost:10});
  const got=r.notes.map(n=>Hum.name(n.pitch)).join(' '); const ok=got===want; pass+=ok; console.log(ok?'PASS':'FAIL',name.padEnd(44),'want',want.padEnd(16),'got',got); }
console.log(pass+'/'+cases.length);
