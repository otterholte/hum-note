"""Adds the learned onset detector (onset_weights.json) to the app core and lets it confirm/veto same-pitch splits.
  HP.onMode 0 off | 1 a split must have an onset (prob >= onTh) | 2 undo only if no onset AND no level rise | 3 also add splits where prob >= onAdd
usage: python add_onsets.py <in.html> <out.html>"""
import sys, json, os
src, dst = sys.argv[1], sys.argv[2]; s = open(src, encoding="utf-8").read(); W = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "onset_weights.json")))
def rep(a, b):
    global s; assert s.count(a) == 1, a[:80]; s = s.replace(a, b)
rep("veto: 2.5,", "veto: 2.5, onMode: 0, onTh: 0.5, onAdd: 0.9,")
fn = f"""  // Note-start detector, learned from 45 sung songs with exact note timings (a weighted sum of what the voice does
  // in the 120 ms around each frame: voicing, loudness, sound colour, vibrato, pitch change, level rise/fall).
  // Returns, for every frame, the chance that a new note starts there.
  const ONSET={json.dumps(W)};
  function onsetProb(F){{ const n=F.n, m=F.m, vo=F.voiced, ds=F.ds, nv=F.nv||new Float32Array(n), vib=F.vib||new Uint8Array(n), W=ONSET.w, OFF=ONSET.off;
    const so=Array.from(ds).sort((a,b)=>a-b), pk=so[Math.min(n-1,Math.round(0.97*(n-1)))]||0;
    const med=(i,lo,hi)=>{{ const v=[]; for(let q=Math.max(0,i+lo);q<Math.max(0,i+hi)&&q<n;q++) if(vo[q]&&isFinite(m[q])) v.push(m[q]); if(v.length<3) return NaN; v.sort((a,b)=>a-b); const h=v.length>>1; return v.length&1?v[h]:(v[h-1]+v[h])/2; }};
    const p=new Float32Array(n);
    for(let i=0;i<n;i++){{ let z=ONSET.b, k=0;
      for(const o of OFF){{ const j=((i+o)%n+n)%n; z+=W[k++]*vo[j]+W[k++]*(ds[j]-pk)+W[k++]*nv[j]+W[k++]*vib[j]; }}
      let dp=Math.abs(med(i,1,9)-med(i,-8,0)); if(!isFinite(dp)) dp=0;
      let hi=-1e9,lo=1e9,hf=-1e9; for(let q=i;q<Math.min(n,i+10);q++) hi=Math.max(hi,ds[q]); for(let q=Math.max(0,i-4);q<Math.min(n,i+2);q++) lo=Math.min(lo,ds[q]); for(let q=Math.max(0,i-12);q<i;q++) hf=Math.max(hf,ds[q]);
      const rise=i+2<=n?hi-lo:0, fall=i>0?hf-lo:0;
      z+=W[k++]*dp+W[k++]*Math.min(dp,3)+W[k++]*rise+W[k++]*fall; p[i]=1/(1+Math.exp(-z)); }}
    const sm=new Float32Array(n); for(let i=0;i<n;i++) sm[i]=(p[Math.max(0,i-1)]*(i>0)+p[i]+(i<n-1?p[i+1]:0))/3; return sm; }}
"""
rep("  function decode(F,tune,key,opt){\n", fn + "  function decode(F,tune,key,opt){\n    const OP=HP.onMode?onsetProb(F):null, opk=(c,r)=>{ let v=0; for(let q=Math.max(0,c-r);q<Math.min(F.n,c+r+1);q++) v=Math.max(v,OP[q]); return v; };\n")
rep("          if(R-lo<HP.veto){", "          const on=OP?opk(c,5):1; if(HP.onMode===1?on<HP.onTh:(R-lo<HP.veto&&(HP.onMode<2||on<HP.onTh))){")
rep("      cuts.sort((x,y)=>x[0]-y[0]);", "      if(OP&&HP.onMode===3) for(let i=a+10;i<b-10;i++) if(OP[i]>=HP.onAdd&&OP[i]===opk(i,6)&&!cuts.some(c=>Math.abs(c[0]-i)<12)) cuts.push([i,i+1]);\n      cuts.sort((x,y)=>x[0]-y[0]);")
open(dst, "w", encoding="utf-8").write(s); print("added onset detector")
