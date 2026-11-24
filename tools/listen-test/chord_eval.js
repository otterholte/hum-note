// How often the sheet music's automatic chords match the standard chords of well-known tunes, using the app's own
// tempo + bar-line finder + chord picker on performances with human timing wobble. usage: node chord_eval.js [index.html] [--list]
const fs=require('fs'), path=require('path'); const html=process.argv[2]&&!process.argv[2].startsWith('--')?process.argv[2]:path.join(__dirname,'..','..','index.html'), list=process.argv.includes('--list');
const H=fs.readFileSync(html,'utf8'); const Hum=new Function(H.match(/<script id="core">([\s\S]*?)<\/script>/)[1]+';return Hum;')();
const main=H.match(/<script>\n?([\s\S]*?)<\/script>\s*<\/body>/)?.[1]||[...H.matchAll(/<script>([\s\S]*?)<\/script>/g)].pop()[1];
const grab=name=>{ const i=main.indexOf('function '+name+'('); let d=0,j=main.indexOf('{',i); for(;j<main.length;j++){ if(main[j]==='{') d++; else if(main[j]==='}'){ d--; if(!d) break; } } return main.slice(i,j+1); };
const st={chordOver:{},chRate:process.env.RATE||'auto',chShift:0,chStyle:'held',tr:0,res:{key:{tonic:0,mode:'major'}}};
const cm=main.match(/const CHORD_MODEL=[^\r\n]*/); const scoreChords=new Function('st','Hum',(process.env.OLD?'':grab('chordHMM')+(cm?cm[0]:''))+grab('chordOf')+grab('scoreScale')+grab('scoreChords')+';return scoreChords;')(st,Hum);
const TUNES=require('./tunes.js'); let seed=5; const rnd=()=>(seed=(seed*1664525+1013904223)>>>0)/4294967296, gauss=()=>{ let u=0; for(let i=0;i<6;i++) u+=rnd(); return (u-3)/Math.sqrt(0.5); };
const NAME=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'];
let hit=0,tot=0; const per={};
for(const [name,T] of Object.entries(TUNES)) for(let r=0;r<8;r++){
  const bpm=70+rnd()*70, beat=60/bpm, t0=0.3+rnd()*0.5, drift=(rnd()-0.5)*0.12, time=b=>t0+b*beat*(1+drift*b/40); let b=0; const notes=[];
  for(const [p,len] of T.notes){ const s=time(b)+gauss()*0.025; notes.push({start:s,end:Math.max(s+0.06,time(b+len)-0.05-rnd()*0.05),pitch:p}); b+=len; }
  const tp=Hum.tempo(notes), M=Hum.meter(notes,tp), ts=M.ts; st.ts=ts; const unit=M.beat/4, barLen=ts*4, barDur=M.beat*ts, first=notes[0].start;
  const bar0=M.down+Math.floor((first-M.down)/barDur+0.02)*barDur;
  const N=notes.map(n=>{ let u0=Math.round((n.start-bar0)/unit), u1=Math.round((n.end-bar0)/unit); if(u0<0) u0=0; if(u1<=u0) u1=u0+1; return {u0,u1,p:n.pitch,n}; });
  const CH=scoreChords(N,barLen); const at=t=>{ const u=(t-bar0)/unit; let c=null; for(const x of CH.names) if(x.u0<=u+1e-6) c=x; return c?NAME[c.root]:'-'; };
  // compare in the middle of each half bar of the real tune
  let h=0,n=0; T.chords.forEach((lab,i)=>{ const parts=lab.split('/'); for(let q=0;q<2;q++){ const want=parts[parts.length===2?q:0]; const tb=T.pickup+i*T.meter+(q+0.5)*T.meter/2; const got=at(time(tb)); n++; if(got===want) h++; } });
  hit+=h; tot+=n; (per[name]=per[name]||[]).push(Math.round(100*h/n));
  if(list) console.log(`${name} #${r+1}: ${ts}/4  ${CH.names.map(c=>NAME[c.root]).join(' ')}  (${Math.round(100*h/n)}%)`); }
for(const [k,v] of Object.entries(per)) console.log(k.padEnd(24), (v.reduce((a,b)=>a+b)/v.length).toFixed(0)+'%');
console.log('chords right', (100*hit/tot).toFixed(1)+'%');
