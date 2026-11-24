// Scores a fully-labelled set (HumTrans): whole-melody note accuracy (best transposition) and
// note F1 (pitch right + start within 100 ms). node score_ht.js <set> [--list]
const fs=require('fs'), path=require('path'); const set=process.argv[2], list=process.argv.includes('--list');
const idx=JSON.parse(fs.readFileSync(path.join(__dirname,set,'index.json'),'utf8'));
function ed(a,b){ const D=[...Array(a.length+1)].map(()=>Array(b.length+1).fill(0)); for(let i=0;i<=a.length;i++) D[i][0]=i; for(let j=0;j<=b.length;j++) D[0][j]=j;
  for(let i=1;i<=a.length;i++) for(let j=1;j<=b.length;j++) D[i][j]=Math.min(D[i-1][j]+1,D[i][j-1]+1,D[i-1][j-1]+(a[i-1]===b[j-1]?0:1)); return D[a.length][b.length]; }
let A=0,F=0,O=0,n=0,shifts={}; const rows=[];
for(const [name,c] of Object.entries(idx)){ const f=path.join(__dirname,'out_'+set,name+'.json'); if(!fs.existsSync(f)) continue;
  const N=JSON.parse(fs.readFileSync(f,'utf8')).notes, got=N.map(x=>x.pitch); let best={acc:-9,sh:0};
  for(let sh=-24;sh<=24;sh++){ const acc=1-ed(got,c.ref.map(p=>p+sh))/c.ref.length; if(acc>best.acc) best={acc,sh}; }
  // timing F1 at that transposition; also onset-only F1 (any pitch)
  const R=c.ref.map((p,i)=>({p:p+best.sh,t:c.times[i][0]})), used=new Set(); let tp=0, tpo=0; const usedO=new Set();
  for(const g of N){ let k=R.findIndex((r,i)=>!used.has(i)&&r.p===g.pitch&&Math.abs(r.t-g.start)<=0.1); if(k>=0){ used.add(k); tp++; }
    let q=R.findIndex((r,i)=>!usedO.has(i)&&Math.abs(r.t-g.start)<=0.1); if(q>=0){ usedO.add(q); tpo++; } }
  const f1=2*tp/(N.length+R.length), on=2*tpo/(N.length+R.length);
  A+=Math.max(0,best.acc); F+=f1; O+=on; n++; shifts[best.sh]=(shifts[best.sh]||0)+1; rows.push(`${(100*Math.max(0,best.acc)).toFixed(0).padStart(4)}%  F1 ${(100*f1).toFixed(0).padStart(3)}  onset ${(100*on).toFixed(0).padStart(3)}  got ${N.length} ref ${R.length}  ${name}`); }
if(list) console.log(rows.sort().join('\n'));
console.log(`AVERAGE ${(100*A/n).toFixed(1)}% notes | F1 ${(100*F/n).toFixed(1)} | onsets ${(100*O/n).toFixed(1)} over ${n}  (transpositions ${JSON.stringify(shifts)})`);
