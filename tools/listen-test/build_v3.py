"""Builds a v3 test copy of the app (from index.html = v2) with chosen changes. usage: python build_v3.py <out.html> opt[=val] ...
  tail=S,DB    merge a short (<S s) piece split off a held note when it is DB quieter (the note's own consonant)
  scoop=S,ST   a short note (<S s) right before/after a longer one within ST semitones is a slide into/out of it
  disagree=ST,C  also use the AI pitch where the classic detector is ST+ semitones away from it (model confidence C+)
  vibdip=DB    inside vibrato, a level dip must be DB deep (not 5) to split a held note"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); out = sys.argv[1]
opts = dict((a.split("=") + [""])[:2] for a in sys.argv[2:])
s = open(os.path.join(HERE, "..", "..", "index.html"), encoding="utf-8").read()
def rep(a, b):
    global s; assert s.count(a) == 1, a[:70]; s = s.replace(a, b)
if "tail" in opts:
    SH, DB = opts["tail"].split(",")
    rep("      const out=[]; let st=a; cuts.forEach(([c0,c1])=>{ out.push([st,c0,1]); st=c1; }); out.push([st,b,0]); out.forEach((p,i)=>p[2]=i>0?1:0); return out;",
f"""      let out=[]; let st=a; cuts.forEach(([c0,c1])=>{{ out.push([st,c0,1]); st=c1; }}); out.push([st,b,0]);
      // a short, clearly quieter piece at either side of a cut is the note's own consonant ("strea-m", "r-ow"), not a new syllable
      {{ const pk=(x,y)=>{{ let v=-99; for(let q=x;q<y;q++) v=Math.max(v,ds[q]); return v; }}, SH=Math.round({SH}/F.dt);
        for(let k=out.length-1;k>0;k--){{ const P=out[k-1], Q=out[k], dP=P[1]-P[0], dQ=Q[1]-Q[0];
          if((dQ<SH&&dP>=2*dQ&&pk(Q[0],Q[1])<pk(P[0],P[1])-{DB})||(dP<SH&&dQ>=2*dP&&pk(P[0],P[1])<pk(Q[0],Q[1])-{DB})){{ P[1]=Q[1]; out.splice(k,1); }} }} }}
      out.forEach((p,i)=>p[2]=i>0?1:0); return out;""")
if "vibdip" in opts:
    rep("if(ds[i]<L-5&&ds[i]<R-5&&", f"const dd=(F.vib&&F.vib[i])?{opts['vibdip']}:5; if(ds[i]<L-dd&&ds[i]<R-dd&&")
for key in ("scoop", "scoopend"):
  if key in opts:
    S, ST = opts[key].split(",")[:2]; R = (opts[key].split(",") + ["2"])[2]; G = 1 if "nbguard" in opts else 0
    a = "    // octave slips: a note an octave away from BOTH neighbours" if key == "scoop" else "    return kept.map(o=>{\n      const dev=[],lv=[];"
    rep(a, f"""    // slides: a very short note that runs straight into (or out of) a longer note a step or two away, with no
    // break in the voice, is the voice travelling to that note, not a note of its own
    {{ const G={G}, SF=Math.round({S}/F.dt); for(let k=0;k<kept.length;k++){{ const o=kept[k], d=o.b-o.a; if(d>=SF) continue; const nx=kept[k+1], pv=kept[k-1];
        if(G&&pv&&nx&&pv.pitch===nx.pitch&&pv.pitch!==o.pitch&&d>=Math.round(0.08/F.dt)) continue; // X Y X: a real neighbour note
        const ok=x=>x&&x.pitch!==o.pitch&&Math.abs(x.pitch-o.pitch)<={ST}&&(x.b-x.a)>={R}*d;
        if(ok(nx)&&nx.a-o.b<=2){{ nx.a=o.a; kept.splice(k,1); k--; continue; }}
        if(ok(pv)&&o.a-pv.b<=2){{ pv.b=o.b; kept.splice(k,1); k--; }} }} }}
""" + a)
if "disagree" in opts:
    D, C = opts["disagree"].split(",")
    rep("for(let j=Math.max(0,i-W);j<=Math.min(n-1,i+W);j++) m[j]=1; return m; }",
f"""for(let j=Math.max(0,i-W);j<=Math.min(n-1,i+W);j++) m[j]=1;
    // where the classic detector jumps to a different note than the AI model (it locks onto an overtone:
    // a fifth or an octave off), trust the model for those frames
    {{ let k=0; for(let i=0;i<n;i++){{ const t=tr.t0+i*tr.dt; while(k+1<sw.t.length&&sw.t[k+1]<=t) k++; const f=sw.f0[k];
        if(tr.ap[i]<0.3&&f>0&&sw.conf[k]>={C}&&Math.abs(12*Math.log2(tr.f0[i]/f))>{D}) for(let j=Math.max(0,i-2);j<=Math.min(n-1,i+2);j++) m[j]=1; }} }}
    return m; }}""")
open(out, "w", encoding="utf-8").write(s); print("built", out, opts)
