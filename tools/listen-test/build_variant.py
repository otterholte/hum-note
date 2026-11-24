"""Builds a test copy of the app with chosen detection changes switched on.
usage: python build_variant.py <out.html> [nb] [nv] [recenter] [mask]
  nb        X, X±1, X where the middle is the same note sung flat/sharp -> X
  nv        split same-pitch syllables at a change of vowel/consonant (outside vibrato)
  recenter  keep note names on the nearest A440 semitone
  mask      AI pitch (SwiftF0) only in vibrato stretches; classic detector elsewhere"""
import sys, subprocess, os
HERE = os.path.dirname(os.path.abspath(__file__)); out = sys.argv[1]; opts = set(sys.argv[2:])
s = open(os.path.join(HERE, "..", "..", "index.html"), encoding="utf-8").read()
def rep(a, b, n=1):
    global s; assert s.count(a) == n, a[:60]; s = s.replace(a, b)

if "nb" in opts:
    a = "      // h) a passing note: between two notes a step or more apart"
    rep(a, """      // i) X, X±1, X where the middle note's sung centre is within ~0.7 st of X: the same note sung a little
      //    flat/sharp (often with wide vibrato), not a real neighbour note — a real neighbour sits on its own pitch
      { for(let k=1;k<fin.length-1;k++){ const p=fin[k-1], o=fin[k], q=fin[k+1]; if(p.pitch!==q.pitch||Math.abs(o.pitch-p.pitch)!==1||o.orn) continue;
          if(o.a-p.b>Math.round(0.25/F.dt)||q.a-o.b>Math.round(0.25/F.dt)) continue;
          const c=(o.b-o.a)*F.dt>=0.25?base(o):center(o); if(Math.abs(c-p.pitch)<0.7) o.pitch=p.pitch; }
        const out2=[]; for(const o of fin){ const p=out2[out2.length-1]; if(p&&p.pitch===o.pitch&&!o.cut&&o.a-p.b<=3){ p.b=o.b; continue; } out2.push(o); } fin=out2; }
""" + a)

if "nv" in opts:
    tmp = out + ".tmp.html"; open(tmp, "w", encoding="utf-8").write(s)
    subprocess.run([sys.executable, os.path.join(HERE, "patch_nv.py"), tmp, tmp, "5", "0.5", "99"], check=True, capture_output=True)
    s = open(tmp, encoding="utf-8").read(); os.remove(tmp)

if "recenter" in opts:
    a = "  // the key that makes the most musical sense once drift is allowed for (every key is tried)"
    rep(a, """  // keep note names on the nearest standard (A440) semitone: if the singer's tuning estimate has wandered
  // more than half a semitone away overall, shift the grid by one semitone (and the key with it)
  function recenter(tune,key){ const c=tune.curve; if(!c.length) return key; let s=0; for(let i=0;i<c.length;i++) s+=c[i]; const mean=s/c.length; const sh=mean>0.5?-1:mean<-0.5?1:0; if(!sh) return key;
    for(let i=0;i<c.length;i++) c[i]+=sh; if(!key) return key; const t=((key.tonic-sh)%12+12)%12; return {...key,tonic:t,scale:(key.mode==='major'?SC_MAJ:SC_MIN).map(i=>(i+t)%12),name:FLATS[t]+' '+key.mode}; }
""" + a)
    rep("applyDrift,useSwift,", "applyDrift,recenter,useSwift,")

if "mask" in opts:
    rep("function useSwift(tr,sw){", """function swiftMask(tr,sw){ const F=frames(useSwift({...tr,f0:tr.f0.slice(),ap:tr.ap.slice(),db:tr.db.slice(),ds:tr.ds.slice()},sw)), n=tr.n, m=new Uint8Array(n), W=15; for(let i=0;i<n;i++) if(F.vib[i]) for(let j=Math.max(0,i-W);j<=Math.min(n-1,i+W);j++) m[j]=1; return m; }
  function useSwift(tr,sw,mask){""")
    rep("  for(let i=0;i<n;i++){ const t=t0+i*dt; while(k+1<T.length&&T[k+1]<=t) k++;", "  for(let i=0;i<n;i++){ const t=t0+i*dt; while(k+1<T.length&&T[k+1]<=t) k++; if(mask&&!mask[i]) continue;")
    rep("  tr.swift=true; return tr; }", "  if(!mask) tr.swift=true; return tr; }")
    rep("useSwift,NAMES", "useSwift,swiftMask,NAMES")
open(out, "w", encoding="utf-8").write(s); print("built", out, sorted(opts))
