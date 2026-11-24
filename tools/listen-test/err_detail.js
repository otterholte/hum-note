// Lists every error with its timing so patterns show up. node err_detail.js <set> [clip-substring]
const fs=require('fs'), path=require('path'); const set=process.argv[2]||'bench', only=process.argv[3];
const idx=JSON.parse(fs.readFileSync(path.join(__dirname,set,'index.json'),'utf8'));
function align(a,b){ const n=a.length,m=b.length, D=[...Array(n+1)].map(()=>Array(m+1).fill(0)); for(let i=0;i<=n;i++) D[i][0]=i; for(let j=0;j<=m;j++) D[0][j]=j;
  for(let i=1;i<=n;i++) for(let j=1;j<=m;j++) D[i][j]=Math.min(D[i-1][j]+1,D[i][j-1]+1,D[i-1][j-1]+(a[i-1]===b[j-1]?0:1)); return D; }
const big={}, ext=[]; 
for(const [name,c] of Object.entries(idx)){ if(only&&!name.includes(only)) continue; const f=path.join(__dirname,'out_'+set,name+'.json'); if(!c.ref||!fs.existsSync(f)) continue;
  const J=JSON.parse(fs.readFileSync(f,'utf8')), N=J.notes, got=N.map(n=>n.pitch); let best=null;
  for(let sh=-30;sh<=30;sh++){ const ref=c.ref.map(p=>p+sh), D=align(got,ref); for(let j=Math.max(3,Math.floor(got.length*0.5));j<=ref.length;j++){ const acc=1-D[got.length][j]/j; if(!best||acc>best.acc) best={acc,j,ref,D}; } }
  const {j,ref,D}=best; let i=got.length, k=j; const rows=[];
  const vf=n=>{ let v=0,t=0; for(let q=Math.round((n.start-J.t0)/J.dt);q<Math.round((n.end-J.t0)/J.dt);q++){ t++; if(J.vib[q]) v++; } return t?v/t:0; };
  while(i>0||k>0){ if(i>0&&k>0&&D[i][k]===D[i-1][k-1]+(got[i-1]===ref[k-1]?0:1)){ const n=N[i-1], d=got[i-1]-ref[k-1]; rows.push(`${d?'SUB'+(d>0?'+':'')+d:'ok  '} ${n.start.toFixed(2)}-${n.end.toFixed(2)} got ${n.pitch} ref ${ref[k-1]} c${n.cents} vib${vf(n).toFixed(1)}`); if(Math.abs(d)>2) big[d]=(big[d]||0)+1; i--; k--; }
    else if(i>0&&D[i][k]===D[i-1][k]+1){ const n=N[i-1]; rows.push(`EXTRA ${n.start.toFixed(2)}-${n.end.toFixed(2)} got ${n.pitch} dur ${(n.end-n.start).toFixed(2)} vib${vf(n).toFixed(1)} nb ${got[i-2]},${got[i]}`); ext.push({d:n.end-n.start,v:vf(n),same:[got[i-2],got[i]].includes(n.pitch)}); i--; }
    else { rows.push(`MISS ref ${ref[k-1]}`); k--; } }
  if(only) console.log('== '+name+' '+(best.acc*100).toFixed(0)+'%\n'+rows.reverse().join('\n')); }
console.log('big subs by diff', big);
const h={}; for(const e of ext){ const b=(e.same?'same ':'other ')+(e.d<0.15?'<.15':e.d<0.3?'<.3':e.d<0.6?'<.6':'.6+')+(e.v>0.5?' vib':''); h[b]=(h[b]||0)+1; } console.log('extras', h);
