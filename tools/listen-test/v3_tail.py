"""v3 experiment: merge a short, quieter piece split off the start/end of a held note (a consonant, not a syllable).
usage: python v3_tail.py <in.html> <out.html> SHORT_S DB"""
import sys
src,dst,SH,DB=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4]; s=open(src,encoding="utf-8").read()
old="      const out=[]; let st=a; cuts.forEach(([c0,c1])=>{ out.push([st,c0,1]); st=c1; }); out.push([st,b,0]); out.forEach((p,i)=>p[2]=i>0?1:0); return out;"
new=f"""      let out=[]; let st=a; cuts.forEach(([c0,c1])=>{{ out.push([st,c0,1]); st=c1; }}); out.push([st,b,0]);
      // a short, clearly quieter piece at either side of a cut is the note's own consonant ("strea-m", "r-ow"), not a new syllable
      {{ const pk=(x,y)=>{{ let v=-99; for(let q=x;q<y;q++) v=Math.max(v,ds[q]); return v; }}, SH=Math.round({SH}/F.dt);
        for(let k=out.length-1;k>0;k--){{ const P=out[k-1], Q=out[k], dP=P[1]-P[0], dQ=Q[1]-Q[0];
          if((dQ<SH&&dP>=2*dQ&&pk(Q[0],Q[1])<pk(P[0],P[1])-{DB})||(dP<SH&&dQ>=2*dP&&pk(P[0],P[1])<pk(Q[0],Q[1])-{DB})){{ P[1]=Q[1]; out.splice(k,1); }} }} }}
      out.forEach((p,i)=>p[2]=i>0?1:0); return out;"""
assert s.count(old)==1; s=s.replace(old,new); open(dst,"w",encoding="utf-8").write(s)
