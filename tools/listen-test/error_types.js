// Breaks a set's errors into kinds (best alignment per clip, like score_set.js). node error_types.js <set>
const fs=require('fs'), path=require('path'); const set=process.argv[2]||'bench';
const idx=JSON.parse(fs.readFileSync(path.join(__dirname,set,'index.json'),'utf8'));
function align(a,b){ const n=a.length,m=b.length, D=[...Array(n+1)].map(()=>Array(m+1).fill(0)); for(let i=0;i<=n;i++) D[i][0]=i; for(let j=0;j<=m;j++) D[0][j]=j;
  for(let i=1;i<=n;i++) for(let j=1;j<=m;j++) D[i][j]=Math.min(D[i-1][j]+1,D[i][j-1]+1,D[i-1][j-1]+(a[i-1]===b[j-1]?0:1)); return D; }
const tally={ok:0,sub1:0,sub2:0,subBig:0,extra:0,extraSame:0,extraSemi:0,missing:0,missingRepeat:0}; let refN=0;
for(const [name,c] of Object.entries(idx)){ const f=path.join(__dirname,'out_'+set,name+'.json'); if(!c.ref||!fs.existsSync(f)) continue;
  const got=JSON.parse(fs.readFileSync(f,'utf8')).notes.map(n=>n.pitch); let best=null;
  for(let sh=-30;sh<=30;sh++){ const ref=c.ref.map(p=>p+sh), D=align(got,ref); for(let j=Math.max(3,Math.floor(got.length*0.5));j<=ref.length;j++){ const acc=1-D[got.length][j]/j; if(!best||acc>best.acc) best={acc,j,ref,D}; } }
  const {j,ref,D}=best; refN+=j; let i=got.length, k=j;
  while(i>0||k>0){ if(i>0&&k>0&&D[i][k]===D[i-1][k-1]+(got[i-1]===ref[k-1]?0:1)){ const d=Math.abs(got[i-1]-ref[k-1]); if(!d) tally.ok++; else if(d===1) tally.sub1++; else if(d===2) tally.sub2++; else tally.subBig++; i--; k--; }
    else if(i>0&&D[i][k]===D[i-1][k]+1){ tally.extra++; const nb=[got[i-2],got[i]].filter(x=>x!=null); if(nb.includes(got[i-1])) tally.extraSame++; else if(nb.some(x=>Math.abs(x-got[i-1])===1)) tally.extraSemi++; i--; }
    else { tally.missing++; if(ref[k-2]===ref[k-1]||ref[k]===ref[k-1]) tally.missingRepeat++; k--; } } }
console.log(`reference notes ${refN}`); for(const [k,v] of Object.entries(tally)) console.log(k.padEnd(14),v);
