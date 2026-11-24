"""Inside vibrato, a level dip only splits a held note if it is clearly deeper (HP.vibX dB) than the singer's own
loudness wobble in that stretch (measured around it). usage: python add_vibadapt.py <in.html> <out.html>"""
import sys
src, dst = sys.argv[1], sys.argv[2]; s = open(src, encoding="utf-8").read()
def rep(a, b):
    global s; assert s.count(a) == 1, a[:80]; s = s.replace(a, b)
rep("veto: 2.5,", "veto: 2.5, vibAdapt: 1, vibX: 2,")
rep("if(ds[i]<L-HP.dip&&ds[i]<R-HP.dip&&", "const dd=(HP.vibAdapt&&F.vib&&F.vib[i])?Math.max(HP.dip,amDepth(i)+HP.vibX):HP.dip; if(ds[i]<L-dd&&ds[i]<R-dd&&")
A = "    // runs -> notes, splitting repeated notes at syllable gaps / energy dips\n"
rep(A, """    // how much the voice's loudness naturally wobbles with the vibrato around frame i (typical swing, dB)
    const amC=new Map(); const amDepth=i=>{ const key=i>>3; if(amC.has(key)) return amC.get(key); const sw=[];
      for(let c=Math.max(0,i-45);c+19<Math.min(n,i+45);c+=6){ if(Math.abs(c+9-i)<10) continue; let hi=-99,lo=99,ok=true; for(let q=c;q<c+19;q++){ if(!voiced[q]){ ok=false; break; } hi=Math.max(hi,ds[q]); lo=Math.min(lo,ds[q]); } if(ok) sw.push(hi-lo); }
      const v=sw.length?median(sw):0; amC.set(key,v); return v; };
""" + A)
open(dst, "w", encoding="utf-8").write(s); print("added adaptive vibrato dip")
