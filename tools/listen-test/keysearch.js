const fs=require('fs'); const H=fs.readFileSync('S:/Coding Projects/HumToMidi/index.html','utf8');
const grab=name=>{ const i=H.indexOf('function '+name+'('); let d=0,j=H.indexOf('{',i); for(;j<H.length;j++){ if(H[j]==='{') d++; else if(H[j]==='}'){ d--; if(!d) break; } } return H.slice(i,j+1); };
const consts=[/const KK_MAJ=[^\r\n]*/,/const ACC_MAJ=[^\r\n]*/,/const KEY_NAMES=[^\r\n]*/,/const keyPcs=[^\r\n]*/,/const KEY_W=[^\r\n]*/].map(r=>H.match(r)[0]).join('\n');
const rankKeys=new Function(consts+';'+grab('rankKeys')+';return rankKeys;')();
const D='S:/Coding Projects/HumToMidi/tools/listen-test/'; const T=require(D+'tunes.js'), N=JSON.parse(fs.readFileSync(D+'nott.json','utf8'));
const items={tune:[],tuneRiff:[],nA:[],nB:[],nAr:[],nBr:[]};
for(const t of Object.values(T)) for(let sh=0;sh<12;sh++){ let b=0; const notes=t.notes.map(([p,l])=>{ const o={pitch:p+sh,start:b*0.5,end:(b+l)*0.5-0.05}; b+=l; return o; }); items.tune.push([notes,sh,'major']); items.tuneRiff.push([notes.slice(0,8),sh,'major']); }
Object.keys(N).sort().forEach((k,i)=>{ const t=N[k], notes=t.mel.map(([s,e,p])=>({pitch:p,start:s*0.5,end:e*0.5})), m=t.minor?'minor':'major'; const A=i%2?'B':'A';
  items['n'+A].push([notes,t.tonic,m]); items['n'+A+'r'].push([notes.filter(n=>n.start<4*t.meter*0.5),t.tonic,m]); });
items.minA=items.nA.filter(x=>x[2]==='minor').concat(items.nAr.filter(x=>x[2]==='minor')); items.minB=items.nB.filter(x=>x[2]==='minor').concat(items.nBr.filter(x=>x[2]==='minor')); console.log('minor items',items.minA.length,items.minB.length);
const acc=(set,W)=>{ let ok=0; for(const [n,t,m] of items[set]){ const R=rankKeys(n,W); if(R.length&&R[0].tonic===t&&R[0].mode===m) ok++; } return 100*ok/items[set].length; };
const score=W=>(acc('tune',W)+acc('tuneRiff',W)+acc('nA',W)+acc('nAr',W)+2*acc('minA',W))/6;
const rep=W=>Object.keys(items).map(k=>k+' '+acc(k,W).toFixed(0)).join('  ');
let W={cov:0.8,last:0.08,first:0.03,long:0.03,acc:0.006,maj:0.01,leap:0.4,lastDur:0}; let best=score(W); console.log('start',best.toFixed(1),rep(W));
for(let round=0;round<3;round++) for(const k of Object.keys(W)) for(const f of [0,0.5,0.75,1.5,2,3,5]){ const C={...W,[k]:f===0?0:(W[k]||0.02)*f}; const sc=score(C); if(sc>best+0.2){ best=sc; W=C; console.log(round,k,'=',+C[k].toFixed(4),'->',sc.toFixed(1)); } }
console.log('best',JSON.stringify(Object.fromEntries(Object.entries(W).map(([k,v])=>[k,+v.toFixed(4)])))); console.log(rep(W));
