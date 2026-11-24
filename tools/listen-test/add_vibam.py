"""Vibrato's own loudness wobble is not a new syllable: inside vibrato, undo a same-pitch split whose level dip lines
up with a low/high point of the pitch swing, unless the dip is deeper than HP.vibAMdb (or the voice actually stops).
usage: python add_vibam.py <in.html> <out.html>"""
import sys
src, dst = sys.argv[1], sys.argv[2]; s = open(src, encoding="utf-8").read()
def rep(a, b):
    global s; assert s.count(a) == 1, a[:80]; s = s.replace(a, b)
rep("veto: 2.5,", "veto: 2.5, vibAM: 1, vibAMdb: 8, vibAMw: 4,")
rep("      out.forEach((p,i)=>p[2]=i>0?1:0); return out;",
"""      // inside vibrato the voice gets louder and softer in step with each pitch swing; a dip that sits on a swing's
      // low (or high) point is that wobble, not a new syllable
      if(HP.vibAM&&F.vib){ const ext=i=>{ const W=5; let mn=true,mx=true; for(let q=i-W;q<=i+W;q++){ if(q===i||q<0||q>=n||!voiced[q]) continue; if(m[q]<m[i]) mn=false; if(m[q]>m[i]) mx=false; }
            if(!(mn||mx)) return false; let s2=0,c2=0; for(let q=i-10;q<=i+10;q++) if(q>=0&&q<n&&voiced[q]){ s2+=m[q]; c2++; } return c2&&Math.abs(m[i]-s2/c2)>0.2; };
        for(let k=out.length-1;k>0;k--){ const c=out[k][0], g=c-out[k-1][1]; if(g>=3) continue; let vb=0; for(let q=c-8;q<=c+8;q++) if(q>=0&&q<n&&F.vib[q]) vb++; if(vb<8) continue;
          let L=-99,R=-99,lo=99; for(let q=Math.max(a,c-14);q<c-3;q++) L=Math.max(L,ds[q]); for(let q=c+3;q<Math.min(b,c+14);q++) R=Math.max(R,ds[q]); for(let q=c-3;q<=c+3;q++) if(q>=0&&q<n) lo=Math.min(lo,ds[q]);
          if(Math.min(L,R)-lo>=HP.vibAMdb) continue; let hit=false; for(let q=c-HP.vibAMw;q<=c+HP.vibAMw;q++) if(q>=0&&q<n&&voiced[q]&&ext(q)){ hit=true; break; }
          if(hit){ out[k-1][1]=out[k][1]; out.splice(k,1); } } }
      out.forEach((p,i)=>p[2]=i>0?1:0); return out;""")
rep("veto: 2.5, vibAM: 1,", "veto: 2.5, vibAM: 1, vibAM2: 1,")
a = "    return kept.map(o=>{\n      const dev=[],lv=[];"
rep(a, """    // after all shaping: two touching pieces of the same note inside vibrato, split exactly at a swing's low/high
    // point with no real break in the voice, are one held note
    if(HP.vibAM2&&F.vib){ const ext=i=>{ let mn=true,mx=true; for(let q=i-5;q<=i+5;q++){ if(q===i||q<0||q>=n||!voiced[q]) continue; if(m[q]<m[i]) mn=false; if(m[q]>m[i]) mx=false; }
          if(!(mn||mx)) return false; let s2=0,c2=0; for(let q=i-10;q<=i+10;q++) if(q>=0&&q<n&&voiced[q]){ s2+=m[q]; c2++; } return c2&&Math.abs(m[i]-s2/c2)>0.2; };
      for(let k=kept.length-1;k>0;k--){ const p=kept[k-1], o=kept[k]; if(p.pitch!==o.pitch||o.a-p.b>2) continue; const c=o.a;
        let vb=0; for(let q=c-8;q<=c+8;q++) if(q>=0&&q<n&&F.vib[q]) vb++; if(vb<8) continue; let unv=0; for(let q=p.b;q<o.a;q++) if(!voiced[q]) unv++; if(unv>1) continue;
        let L=-99,R=-99,lo=99; for(let q=Math.max(0,c-14);q<c-3;q++) L=Math.max(L,ds[q]); for(let q=c+3;q<Math.min(n,c+14);q++) R=Math.max(R,ds[q]); for(let q=c-3;q<=c+3;q++) if(q>=0&&q<n) lo=Math.min(lo,ds[q]);
        if(Math.min(L,R)-lo>=HP.vibAMdb) continue; let hit=false; for(let q=c-HP.vibAMw;q<=c+HP.vibAMw;q++) if(q>=0&&q<n&&voiced[q]&&ext(q)){ hit=true; break; }
        if(hit){ p.b=o.b; kept.splice(k,1); } } }
""" + a)
open(dst, "w", encoding="utf-8").write(s); print("added vibrato wobble rules")
