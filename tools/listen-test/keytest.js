const fs=require('fs'); const H=fs.readFileSync('S:/Coding Projects/HumToMidi/index.html','utf8');
const grab=name=>{ const i=H.indexOf('function '+name+'('); let d=0,j=H.indexOf('{',i); for(;j<H.length;j++){ if(H[j]==='{') d++; else if(H[j]==='}'){ d--; if(!d) break; } } return H.slice(i,j+1); };
const consts=[/const KK_MAJ=[^\r\n]*/,/const ACC_MAJ=[^\r\n]*/,/const KEY_NAMES=[^\r\n]*/,/const keyPcs=[^\r\n]*/].map(r=>H.match(r)[0]).join('\n');
const rankKeys=new Function(consts+';'+grab('rankKeys')+';return rankKeys;')();
const D='S:/Coding Projects/HumToMidi/tools/listen-test/';
const T=require(D+'tunes.js'); const S={};
const tally=(set,R,tonic,mode)=>{ const g=S[set]=S[set]||{n:0,ok:0,top3:0,rel:0}; g.n++; if(!R.length) return; if(R[0].tonic===tonic&&R[0].mode===mode) g.ok++; if(R.slice(0,3).some(r=>r.tonic===tonic&&r.mode===mode)) g.top3++;
  const relT=mode==='major'?(tonic+9)%12:(tonic+3)%12; if(R[0].tonic===relT&&R[0].mode!==mode) g.rel++; };
for(const [name,t] of Object.entries(T)) for(let sh=0;sh<12;sh++){ let b=0; const notes=t.notes.map(([p,l])=>{ const o={pitch:p+sh,start:b*0.5,end:(b+l)*0.5-0.05}; b+=l; return o; });
  tally('tunes whole',rankKeys(notes),sh%12,'major'); tally('tunes riff (8 notes)',rankKeys(notes.slice(0,8)),sh%12,'major'); }
const N=JSON.parse(fs.readFileSync(D+'nott.json','utf8'));
for(const [k,t] of Object.entries(N)){ const notes=t.mel.map(([s,e,p])=>({pitch:p,start:s*0.5,end:e*0.5})); const mode=t.minor?'minor':'major';
  tally('nott whole',rankKeys(notes),t.tonic,mode);
  // a riff: ~4 bars from the start
  const riff=notes.filter(n=>n.start<4*t.meter*0.5); tally('nott riff (4 bars)',rankKeys(riff),t.tonic,mode); }
for(const [k,g] of Object.entries(S)) console.log(k.padEnd(22),`n=${g.n} right ${(100*g.ok/g.n).toFixed(0)}%  in top 3 ${(100*g.top3/g.n).toFixed(0)}%  (picked the relative major/minor ${g.rel})`);
for(const [name,t] of Object.entries(T)){ let b=0; const notes=t.notes.map(([p,l])=>{ const o={pitch:p,start:b*0.5,end:(b+l)*0.5-0.05}; b+=l; return o; }); const R=rankKeys(notes); console.log(name.padEnd(22), R.slice(0,3).map(r=>r.tonic+r.mode[0]+' '+r.r.toFixed(3)).join(' | ')); }
