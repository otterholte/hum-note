"""Turns the note-decision constants in the app's core into named settings (HP.*) with today's values as defaults,
so the tuner can try other values without rebuilding. Behaviour is unchanged. usage: python parametrize.py <in.html> <out.html>"""
import sys
src, dst = sys.argv[1], sys.argv[2]; s = open(src, encoding="utf-8").read()
D = dict(sigma=0.33, kappa=1.2, TN=0, TS=4, gapF=6, gapDip=4, dip=5, nvTh=5.0, nvDip=0.5, tailS=0.16, tailDB=3, veto=2.5,
         minF=0.06, shortF=0.16, glideSlope=0.035, glideStab=0.45, scoopS=0.15, scoopST=2, scoopR=1.5, foldL=0.3, foldSet=0.06, nbFlat=0.7)
def rep(a, b, n=1):
    global s; assert s.count(a) == n, (s.count(a), a[:80]); s = s.replace(a, b)
rep("const Hum = (() => {\n", "const Hum = (() => {\n  // note-decision settings (found by tuning on sung + hummed recordings with known notes); tools can override them\n  const HP = Object.assign(" + repr(D).replace("'", "") .replace("'", "") + ", (typeof globalThis!=='undefined'&&globalThis.HUM_P)||{});\n")
s = s.replace("Object.assign({", "Object.assign({", 1)
rep("opt.sigma||0.33", "opt.sigma||HP.sigma")
rep("*1.2*key.conf", "*HP.kappa*key.conf")
rep("const TN=opt.switchCost||10, TS=4;", "const TN=HP.TN||opt.switchCost||10, TS=HP.TS;")
rep("(e-k>=6||(lo2<L-4&&lo2<R-4))", "(e-k>=HP.gapF||(lo2<L-HP.gapDip&&lo2<R-HP.gapDip))")
rep("if(ds[i]<L-5&&ds[i]<R-5&&", "if(ds[i]<L-HP.dip&&ds[i]<R-HP.dip&&")
rep("if(v<5.0*((F.vib&&F.vib[i])?99:1)) continue;", "if(v<HP.nvTh*((F.vib&&F.vib[i])?99:1)) continue;")
rep("if(lo<Math.min(L,R)-0.5&&", "if(lo<Math.min(L,R)-HP.nvDip&&")
rep("SH=Math.round(0.16/F.dt);", "SH=Math.round(HP.tailS/F.dt);")
rep("pk(Q[0],Q[1])<pk(P[0],P[1])-3)||(dP<SH&&dQ>=2*dP&&pk(P[0],P[1])<pk(Q[0],Q[1])-3)", "pk(Q[0],Q[1])<pk(P[0],P[1])-HP.tailDB)||(dP<SH&&dQ>=2*dP&&pk(P[0],P[1])<pk(Q[0],Q[1])-HP.tailDB)")
rep("if(R-lo<2.5){", "if(R-lo<HP.veto){")
rep("const minF=Math.round(0.06/F.dt);", "const minF=Math.round(HP.minF/F.dt);")
rep("const shortF=Math.round(0.16/F.dt);", "const shortF=Math.round(HP.shortF/F.dt);")
rep("(slope>0.035||stab<0.45)", "(slope>HP.glideSlope||stab<HP.glideStab)")
rep("SF=Math.round(0.15/F.dt);", "SF=Math.round(HP.scoopS/F.dt);")
rep("Math.abs(x.pitch-o.pitch)<=2&&(x.b-x.a)>=1.5*d;", "Math.abs(x.pitch-o.pitch)<=HP.scoopST&&(x.b-x.a)>=HP.scoopR*d;")
rep("          if(L<0.3){", "          if(L<HP.foldL){")
rep("settledAway(o,p.pitch)<0.06", "settledAway(o,p.pitch)<HP.foldSet"); rep("settledAway(o,q.pitch)<0.06", "settledAway(o,q.pitch)<HP.foldSet")
rep("if(Math.abs(c-p.pitch)<0.7) o.pitch=p.pitch;", "if(Math.abs(c-p.pitch)<HP.nbFlat) o.pitch=p.pitch;")
open(dst, "w", encoding="utf-8").write(s); print("parametrized", len(D), "settings")
