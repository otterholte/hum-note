// Compares chord pickers on the 126 held-back Nottingham tunes (true bar lines and key, so only the chord choice is
// tested): the app's current picker vs the learned one. Score = share of beats whose chord root matches the tune's.
// usage: node chord_eval2.js [index.html] [W json]
const fs=require('fs'), path=require('path'), D=__dirname; const html=process.argv[2]||path.join(D,'..','..','index.html'), WJ=process.argv[3]?JSON.parse(process.argv[3]):{};
const H=fs.readFileSync(html,'utf8'); const Hum=new Function(H.match(/<script id="core">([\s\S]*?)<\/script>/)[1]+';return Hum;')();
const main=[...H.matchAll(/<script>([\s\S]*?)<\/script>/g)].pop()[1];
const grab=name=>{ const i=main.indexOf('function '+name+'('); if(i<0) return ''; let d=0,j=main.indexOf('{',i); for(;j<main.length;j++){ if(main[j]==='{') d++; else if(main[j]==='}'){ d--; if(!d) break; } } return main.slice(i,j+1); };
const st={chordOver:{},chRate:'auto',chShift:0,chStyle:'held',tr:0,res:{key:{tonic:0,mode:'major'}}};
const oldPick=new Function('st','Hum',grab('chordOf')+grab('scoreScale')+grab('scoreChords')+';return scoreChords;')(st,Hum);
const chordHMM=require('./chordhmm.js'), MODEL=JSON.parse(fs.readFileSync(path.join(D,'chord_model.json'),'utf8'));
const T=JSON.parse(fs.readFileSync(path.join(D,'nott.json'),'utf8')), names=Object.keys(T).sort().filter((n,i)=>i%5===0);
const Qp={'':0,'7':0,'m':1,'m7':1,'dim':2};
let A={old:[0,0],hmm:[0,0]};
for(const n of names){ const t=T[n], barLen=4*t.meter; const N=t.mel.map(([s,e,p])=>({u0:Math.round(s*4),u1:Math.max(Math.round(s*4)+1,Math.round(e*4)),p}));
  const truth=b=>{ const c=t.chords.find(c=>c[0]<=b+0.01&&c[1]>b+0.01); return c?c[2]:null; };
  st.res.key={tonic:t.tonic,mode:t.minor?'minor':'major'}; st.ts=t.meter;
  const O=oldPick(N,barLen); const oldAt=b=>{ let c=null; for(const x of O.names) if(x.u0<=b*4+0.01) c=x; return c?c.root:null; };
  const R=chordHMM(N,barLen,{tonic:t.tonic,minor:t.minor},MODEL,{W:WJ}); const hmmAt=b=>{ let k=-1; R.segs.forEach((s,i)=>{ if(s[0]<=b*4+0.01) k=i; }); return k>=0?R.chords[k].root:null; };
  const L=Math.ceil(Math.max(...t.mel.map(x=>x[1])));
  for(let b=0;b<L;b++){ const tr=truth(b); if(tr==null) continue; A.old[1]++; A.hmm[1]++; if(oldAt(b)===tr) A.old[0]++; if(hmmAt(b)===tr) A.hmm[0]++; } }
console.log(`held-back tunes ${names.length}: current picker ${(100*A.old[0]/A.old[1]).toFixed(1)}%  learned picker ${(100*A.hmm[0]/A.hmm[1]).toFixed(1)}% of beats with the right chord`);
