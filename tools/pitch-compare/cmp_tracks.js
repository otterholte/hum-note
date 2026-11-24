const fs=require('fs'); const H=fs.readFileSync('../../index.html','utf8'); const Hum=new Function(H.match(/<script id="core">([\s\S]*?)<\/script>/)[1]+';return Hum;')();
const b=fs.readFileSync(process.argv[2]); let o=12,sr=0,ch=1,bits=16,data; while(o<b.length-8){ const id=b.toString('ascii',o,o+4),L=b.readUInt32LE(o+4); if(id==='fmt '){ch=b.readUInt16LE(o+10);sr=b.readUInt32LE(o+12);bits=b.readUInt16LE(o+22);} if(id==='data')data=b.subarray(o+8,o+8+L); o+=8+L+(L&1); }
const n=data.length/(bits/8)/ch, x=new Float32Array(n); for(let i=0;i<n;i++){ let s=0; for(let c=0;c<ch;c++) s+=bits===16?data.readInt16LE((i*ch+c)*2)/32768:data.readFloatLE((i*ch+c)*4); x[i]=s/ch; }
const r=sr/16000, N=Math.floor(n/r), y=new Float32Array(N); for(let i=0;i<N;i++){ let s=0,c=0; for(let k=Math.floor(i*r);k<Math.floor((i+1)*r);k++){ s+=x[k]; c++; } y[i]=s/c; }
const A=Hum.track(y,16000), B=Hum.useSwift(Hum.track(y,16000),JSON.parse(fs.readFileSync(process.argv[3],'utf8')));
const d=[]; let onlyY=0,onlyS=0,oct=0; for(let i=0;i<A.n;i++){ const ya=A.ap[i]<0.3, sa=B.ap[i]<0.3; if(ya&&!sa) onlyY++; if(sa&&!ya) onlyS++; if(ya&&sa){ const c=1200*Math.log2(B.f0[i]/A.f0[i]); if(Math.abs(c)>600) oct++; else d.push(c); } }
d.sort((a,b)=>a-b); const q=p=>d[Math.floor(p*(d.length-1))].toFixed(0);
console.log('frames both',d.length,'swift-yin cents: p10',q(.1),'median',q(.5),'p90',q(.9),'| octave disagreements',oct,'| voiced only YIN',onlyY,'only swift',onlyS);
