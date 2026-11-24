// Prototype of the bar-line finder (meter, beat speed and where bar 1 starts). W = weights of the cues.
// Each candidate grid is scored on: notes landing on beats, long notes landing on beat 1, each bar fitting one
// chord, and long notes not crossing bar lines; plus a mild preference for 60-140 BPM.
module.exports=function meter(notes,tp,W){ W=Object.assign({R:0.5,S:2,H:2,C:9,bpm:1.6,m4:0.075,dbl:0,P:0.5,Sm:1,Hm:0},W||{});
  const N=notes.filter(n=>n.end-n.start>=0.06).sort((a,b)=>a.start-b.start); if(N.length<4||!tp) return {ts:4,beat:tp?tp.beat:0.5,down:tp?tp.phase:0};
  const ioi=N.map((n,i)=>i+1<N.length?N[i+1].start-n.start:(n.end-n.start)+0.1), t0=N[0].start, t1=N[N.length-1].end;
  const TRI=[]; for(let r=0;r<12;r++){ TRI.push([r,(r+4)%12,(r+7)%12]); TRI.push([r,(r+3)%12,(r+7)%12]); }
  const cands=[]; const b0=tp.beat;
  for(const [b,phs,lvl] of [[b0,[tp.phase],0],[b0/2,[tp.phase],1],[b0*2,[tp.phase,tp.phase+b0],2]]){ const bpm=60/b; if(bpm<40||bpm>220) continue;
    for(const ph of phs){ const x=N.map(n=>(n.start-ph)/b), k=x.map(Math.round), dev=x.map((v,i)=>Math.abs(v-k[i]));
      let sw=0,sr=0; N.forEach((n,i)=>{ const w=Math.min(1,(n.end-n.start)/0.25); sw+=w; sr+=w*Math.cos(2*Math.PI*dev[i]); }); const R=sr/sw;
      const kmin=Math.floor((t0-ph)/b)-1, kmax=Math.ceil((t1-ph)/b)+1;
      for(const m of [3,4]) for(let o=0;o<m;o++){ const isDown=kk=>((kk-o)%m+m)%m===0;
        let sd=0,nd=0,so=0,no=0; for(let kk=kmin;kk<=kmax;kk++){ if(isDown(kk)) nd++; else no++; }
        let cross=0; N.forEach((n,i)=>{ if(dev[i]>=0.25) return; const a=Math.min(ioi[i]/b,4); if(isDown(k[i])) sd+=a; else so+=a;
          if(!isDown(k[i])&&ioi[i]/b>=1.5){ const e=k[i]+ioi[i]/b-0.25; for(let kk=k[i]+1;kk<e;kk++) if(isDown(kk)){ cross++; break; } } });
        const Sal=sd/Math.max(1e-9,sd+so)-1/m;
        // each bar: how well its notes fit the best single chord
        let H=0,nb=0; const bar=m*b, d0=ph+o*b; const firstBar=Math.floor((t0-d0)/bar), lastBar=Math.floor((t1-d0)/bar);
        for(let q=firstBar;q<=lastBar;q++){ const a=d0+q*bar, e=a+bar; const dur=new Float64Array(12); let tot=0;
          N.forEach(n=>{ const ov=Math.min(n.end,e)-Math.max(n.start,a); if(ov>0){ dur[((n.pitch%12)+12)%12]+=ov; tot+=ov; } }); if(tot<bar*0.3) continue;
          let best=-1e9; for(const T of TRI){ const f=(dur[T[0]]+dur[T[1]]+dur[T[2]]-0.5*(tot-dur[T[0]]-dur[T[1]]-dur[T[2]]))/tot; if(f>best) best=f; } H+=best; nb++; }
        H=nb?H/nb:0;
        const sc=0;
        // where the first note sits in its bar: most songs start on beat 1, or a beat (or half) before it
        const fx=((N[0].start-d0)/b%m+m)%m, pick=m-fx; const P=(fx<0.25||fx>m-0.25)?1:(pick<=1.25)?0.6:(pick<=2.25)?0.2:0;
        cands.push({sc,ts:m,beat:b,down:d0,bpm,R,Sal,H,cross,P,lvl,ph}); } } }
  // compare the bar-1 positions of the same beat grid and meter with each other (relative salience / chord fit)
  const grp={}; cands.forEach(c=>{ const k=c.beat+'|'+c.ph+'|'+c.ts; (grp[k]=grp[k]||[]).push(c); });
  Object.values(grp).forEach(G=>{ const mS=G.reduce((a,c)=>a+c.Sal,0)/G.length, mH=G.reduce((a,c)=>a+c.H,0)/G.length;
    G.forEach(c=>{ c.sc=W.R*c.R-W.C*c.cross/N.length-W.bpm*Math.abs(Math.log2(c.bpm/95))+(c.ts===4?W.m4:0)-(c.lvl?W.dbl:0)
      +W.S*(c.Sal-mS)+W.H*(c.H-mH)+W.Sm*Math.max(...G.map(x=>x.Sal))+W.Hm*Math.max(...G.map(x=>x.H))+W.P*c.P; }); });
  cands.sort((a,b)=>b.sc-a.sc); const B=cands[0]; return {ts:B.ts,beat:B.beat,down:B.down,bpm:B.bpm}; };
