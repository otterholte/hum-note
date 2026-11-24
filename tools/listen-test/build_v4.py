"""Builds a test copy on top of index.html (v3) with chosen changes. usage: python build_v4.py <out.html> opt[=val] ...
  learned=RISE,NV[,keepgap]   replace the level-dip and vowel-change split rules with the rule learned from CSD:
                              split a held pitch where the level rises RISE dB after a dip AND the sound colour changes (nv > NV)"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); out = sys.argv[1]
opts = dict((a.split("=") + [""])[:2] for a in sys.argv[2:])
s = open(os.path.join(HERE, "..", "..", "index.html"), encoding="utf-8").read()
def rep(a, b):
    global s; assert s.count(a) == 1, a[:70]; s = s.replace(a, b)
if "learned" in opts:
    p = opts["learned"].split(","); RISE, NV = p[0], p[1]
    a1 = s.index("      cuts.sort((x,y)=>x[0]-y[0]);"); a0 = a1 if "keep" in p else s.index("      // energy dips inside voiced stretches (legato")
    s = s[:a0] + f"""      // a new syllable on the same pitch (learned from 50 sung songs with exact note timings): the level dips and
      // then rises again by {RISE}+ dB, while the sound's colour (vowel/consonant) changes
      if(F.nv) for(let i=a+8;i<b-8;i++){{ let lo=99; for(let q=i-3;q<=i+3;q++) lo=Math.min(lo,ds[q]); let nvm=0; for(let q=i-3;q<=i+3;q++) nvm=Math.max(nvm,F.nv[q]);
        const isMin=ds[i]===lo, isPk=F.nv[i]>=nvm; if(!isMin&&!isPk) continue;
        let R=-99; for(let q=i+3;q<=i+12;q++) if(q<b) R=Math.max(R,ds[q]);
        if(R-lo>{RISE}&&nvm>{NV}&&!cuts.some(c=>Math.abs(c[0]-i)<12)) cuts.push([i,i+1]); }}
""" + s[a1:]
if "veto" in opts:
    X = opts["veto"]
    rep("      out.forEach((p,i)=>p[2]=i>0?1:0); return out;", f"""      // learned from 50 sung songs with exact timings: a real new syllable on the same pitch comes back louder after the
      // split ({X}+ dB rise); a split with no such rise is a consonant or vowel change inside one note -> undo it
      {{ for(let k=out.length-1;k>0;k--){{ const c=out[k][0], g=c-out[k-1][1]; if(g>=6) continue; let lo=99,R=-99; for(let q=Math.max(a,c-6);q<Math.min(b,c+4);q++) lo=Math.min(lo,ds[q]); for(let q=c;q<Math.min(b,c+13);q++) R=Math.max(R,ds[q]);
          if(R-lo<{X}){{ out[k-1][1]=out[k][1]; out.splice(k,1); }} }} }}
      out.forEach((p,i)=>p[2]=i>0?1:0); return out;""")
open(out, "w", encoding="utf-8").write(s); print("built", out, opts)
