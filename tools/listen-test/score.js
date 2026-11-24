// Scores Humnote's notes for each clip against the clip's reference melody (key-independent; the clip may
// cover only the start of the melody). node score.js <dir with clips/index.json and out/<name>.json>
const fs=require('fs'), path=require('path'); const dir=process.argv[2];
const idx=JSON.parse(fs.readFileSync(path.join(dir,'clips','index.json'),'utf8'));
const N=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'], nm=p=>N[((p%12)+12)%12]+(Math.floor(p/12)-1);
function ed(a,b){ const D=[...Array(a.length+1)].map(()=>Array(b.length+1).fill(0)); for(let i=0;i<=a.length;i++) D[i][0]=i; for(let j=0;j<=b.length;j++) D[0][j]=j;
  for(let i=1;i<=a.length;i++) for(let j=1;j<=b.length;j++) D[i][j]=Math.min(D[i-1][j]+1,D[i][j-1]+1,D[i-1][j-1]+(a[i-1]===b[j-1]?0:1)); return D; }
const rows=[];
for(const [name,c] of Object.entries(idx)){
  const f=path.join(dir,'out',name+'.json'); if(!fs.existsSync(f)) continue; const d=JSON.parse(fs.readFileSync(f,'utf8'));
  const got=d.notes.map(n=>n.pitch); const r={name,got:got.map(nm).join(' '),n:got.length,key:d.key};
  if(c.ref){ let best=null; for(let sh=-24;sh<=24;sh++){ const ref=c.ref.map(p=>p+sh), D=ed(got,ref);
      for(let j=Math.max(1,Math.floor(got.length*0.5));j<=ref.length;j++){ const e=D[got.length][j]; const acc=1-e/Math.max(j,1); if(!best||acc>best.acc||(acc===best.acc&&j>best.j)) best={acc,j,sh,e}; } }
    r.ref=c.ref.slice(0,best.j).map(p=>nm(p+best.sh)).join(' '); r.score=Math.round(100*best.acc); r.errors=best.e; r.refLen=best.j; }
  rows.push(r); }
fs.writeFileSync(path.join(dir,'results.json'),JSON.stringify(rows,null,1));
rows.forEach(r=>{ console.log(`\n${r.name}${r.score!=null?`   SCORE ${r.score}% (${r.errors} wrong/missing/extra of ${r.refLen})`:''}`); if(r.ref) console.log('  melody : '+r.ref); console.log('  heard  : '+r.got); });
