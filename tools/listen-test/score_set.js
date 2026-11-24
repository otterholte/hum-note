// Scores a set (key-independent, the clip may cover only the start of the melody). node score_set.js <set> [--detail]
const fs=require('fs'), path=require('path'); const set=process.argv[2], detail=process.argv.includes('--detail');
const idx=JSON.parse(fs.readFileSync(path.join(__dirname,set,'index.json'),'utf8'));
const N=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'], nm=p=>N[((p%12)+12)%12]+(Math.floor(p/12)-1);
function ed(a,b){ const D=[...Array(a.length+1)].map(()=>Array(b.length+1).fill(0)); for(let i=0;i<=a.length;i++) D[i][0]=i; for(let j=0;j<=b.length;j++) D[0][j]=j;
  for(let i=1;i<=a.length;i++) for(let j=1;j<=b.length;j++) D[i][j]=Math.min(D[i-1][j]+1,D[i][j-1]+1,D[i-1][j-1]+(a[i-1]===b[j-1]?0:1)); return D; }
let tot=0,cnt=0; const by={}; const rows=[];
for(const [name,c] of Object.entries(idx)){ if(!c.ref) continue; const f=path.join(__dirname,'out_'+set,name+'.json'); if(!fs.existsSync(f)) continue;
  const got=JSON.parse(fs.readFileSync(f,'utf8')).notes.map(n=>n.pitch); let best=null;
  for(let sh=-30;sh<=30;sh++){ const ref=c.ref.map(p=>p+sh), D=ed(got,ref); for(let j=Math.max(3,Math.floor(got.length*0.5));j<=ref.length;j++){ const acc=1-D[got.length][j]/j; if(!best||acc>best.acc||(acc===best.acc&&j>best.j)) best={acc,j,sh}; } }
  const sc=Math.max(0,Math.round(100*best.acc)); tot+=sc; cnt++; const g=name.includes('vibrato')?'vibrato':name.startsWith('synth')?'synthetic':'straight'; (by[g]=by[g]||[]).push(sc);
  rows.push({name,sc,got:got.map(nm).join(' '),ref:c.ref.slice(0,best.j).map(p=>nm(p+best.sh)).join(' ')}); }
rows.sort((a,b)=>a.sc-b.sc);
if(detail) rows.forEach(r=>console.log(`${String(r.sc).padStart(3)}%  ${r.name}\n      melody ${r.ref}\n      heard  ${r.got}`));
else console.log(rows.map(r=>`${String(r.sc).padStart(3)}% ${r.name}`).join('\n'));
const avg=a=>(a.reduce((x,y)=>x+y,0)/a.length).toFixed(1);
console.log(`\nAVERAGE ${(tot/cnt).toFixed(1)}% over ${cnt}  |  `+Object.entries(by).map(([k,v])=>`${k} ${avg(v)}% (${v.length})`).join('  '));
