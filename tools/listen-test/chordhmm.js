// Chord picker learned from 504 harmonised folk tunes (tools/listen-test/train_chords.py -> chord_model.json).
// Works beat by beat: which chord each beat's melody notes suggest (strong beats count more), how chords tend to
// follow each other, and on which beats of the bar chords tend to change. The best path through the whole tune wins.
//   N: melody notes {u0,u1,p} in 16th-note units; barLen: units per bar; scale: {tonic,minor};
//   opt: {rate:'auto'|'bar'|'half'|'beat', shift:beats, forced:{unitStart:{root,pcs}}, W:{emis,...}}
// returns {segs:[[u0,u1]], chords:[{root,q,pcs,label,nm}]}
function chordHMM(N,barLen,scale,M,opt){ opt=opt||{}; const W=Object.assign({emis:1.0,trans:1.0,stay:1.0},opt.W||{});
  const mdl=M[scale.minor?'minor':'major'], S=36, m=Math.max(1,Math.round(barLen/4)), shift=opt.shift||0, rate=opt.rate||'auto';
  const end=Math.max(...N.map(o=>o.u1)), L=Math.max(1,Math.ceil(end/4));
  const Q=[[0,4,7],[0,3,7],[0,3,6]], NM=['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B'], ROM=['I','bII','II','bIII','III','IV','#IV','V','bVI','VI','bVII','VII'];
  const st2ch=s=>{ const deg=Math.floor(s/3), q=s%3, root=(deg+scale.tonic)%12; return {root,q,pcs:Q[q].map(x=>(x+root)%12),label:NM[root]+(q===1?'m':q===2?'°':''),nm:(q===1?ROM[deg].toLowerCase():ROM[deg])+(q===2?'°':'')}; };
  const ch2st=c=>{ const deg=((c.root-scale.tonic)%12+12)%12; const has=i=>c.pcs.includes((c.root+i)%12); return deg*3+(has(3)&&has(6)&&!has(7)?2:has(3)?1:0); };
  // emissions per beat
  const E=[]; for(let b=0;b<L;b++){ const e=new Float64Array(S), pos=((b-shift)%m+m)%m, strong=(pos===0||(m===4&&pos===2))?1:0;
    for(const o of N){ const ov=(Math.min(o.u1,4*b+4)-Math.max(o.u0,4*b))/4; if(ov<=0) continue; const sg=strong&&o.u0<=4*b+0.5?1:0, pc=((o.p-scale.tonic)%12+12)%12;
      for(let s=0;s<S;s++) e[s]+=W.emis*ov*mdl.emis[s][sg][pc]; }
    E.push(e); }
  // which beats may start a new chord
  const may=b=>{ const pos=((b-shift)%m+m)%m; return rate==='beat'?true:rate==='bar'?pos===0:rate==='half'?(pos===0||(m%2===0&&pos===m/2)):true; };
  const forced=new Int16Array(L).fill(-1); if(opt.forced){ const ks=Object.keys(opt.forced).map(Number).sort((a,b)=>a-b);
    ks.forEach((u,i)=>{ const s=ch2st(opt.forced[u]), b0=Math.round(u/4); let b1=b0+1; while(b1<L&&!may(b1)) b1++; for(let b=b0;b<b1&&b<L;b++) forced[b]=s; }); }
  const key=b=>`${m}:${((b-shift)%m+m)%m}`, chg=b=>mdl.change[key(b)]??-0.7, sty=b=>mdl.stay[key(b)]??-0.7;
  let cost=Float64Array.from({length:S},(_,s)=>mdl.prior[s]+E[0][s]+(forced[0]>=0&&forced[0]!==s?-1e6:0)); const back=[];
  for(let b=1;b<L;b++){ const nc=new Float64Array(S), bk=new Int16Array(S); const canChange=may(b);
    for(let s=0;s<S;s++){ let bv=cost[s]+W.stay*sty(b), bs=s; if(canChange) for(let r=0;r<S;r++){ if(r===s) continue; const v=cost[r]+W.stay*chg(b)+W.trans*mdl.trans[r][s]; if(v>bv){ bv=v; bs=r; } }
      nc[s]=bv+E[b][s]+(forced[b]>=0&&forced[b]!==s?-1e6:0); bk[s]=bs; }
    cost=nc; back.push(bk); }
  let s=0; for(let k=1;k<S;k++) if(cost[k]>cost[s]) s=k; const path=new Int16Array(L); path[L-1]=s; for(let b=L-1;b>0;b--){ s=back[b-1][s]; path[b-1]=s; }
  const segs=[], chords=[]; for(let b=0;b<L;){ let e=b+1; while(e<L&&path[e]===path[b]&&!(forced[e]>=0&&forced[e-1]<0)) e++; segs.push([4*b,Math.min(4*e,Math.max(end,4*e))]); const c=st2ch(path[b]); c.set=forced[b]>=0; chords.push(c); b=e; }
  return {segs,chords,path}; }
if(typeof module!=='undefined') module.exports=chordHMM;
