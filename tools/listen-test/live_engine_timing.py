# Note-change timing of the live engine on synthetic voices. usage: python live_engine_timing.py [older live_engine.py]
import sys, time, math, importlib.util, numpy as np
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
new=load(r"S:\Coding Projects\HumToMidi\live_engine.py","new"); old=load(sys.argv[1] if len(sys.argv)>1 else r"S:\Coding Projects\HumToMidi\live_engine.py","old")  # pass an older live_engine.py to compare
sr=44100; rng=np.random.default_rng(1)
def voice(seq):
    out=[]; ph=0; marks=[]; t=0
    for (m0,d,a,glide) in seq:
        n=int(sr*d); prev=marks[-1][1] if marks and marks[-1][1] else m0
        g=int(sr*glide); m=np.full(n,m0,float);
        if g and prev: m[:g]=np.linspace(prev,m0,g)
        m+=0.2*np.sin(2*np.pi*5.5*(t+np.arange(n)/sr))
        f=440*2**((m-69)/12); p=ph+2*np.pi*np.cumsum(f)/sr; ph=p[-1]
        x=sum((0.5/k)*np.sin(k*p) for k in range(1,10))*a*0.1
        marks.append((t,m0 if a>0 else None)); out.append(x); t+=d
    y=np.concatenate(out).astype(np.float32); return y+rng.standard_normal(len(y)).astype(np.float32)*0.0005, marks
# legato line with quick 30 ms slides between notes (how people actually change notes), low and high voice
for base,label in ((0,'low voice (G2-D3)'),(12,'higher voice (G3-D4)')):
    seq=[(43+base,0.3,0,0)]+[(m+base,0.35,1,0.03) for m in (43,47,50,48,47,45,43,50,47,43)]+[(43,0.3,0,0)]
    x,marks=voice(seq)
    for mod,nm in ((old,'before'),(new,'now')):
        for stick in (0.0,0.5):
            A=mod.Analyzer(sr); A.allowed={7,9,11,0,2,4,6}; A.stick=stick; B=32; ev=[]; t0=time.perf_counter()
            for i in range(0,len(x)-B,B):
                for e in A.feed(x[i:i+B]): ev.append(((i+B)/sr,)+e)
            cpu=(time.perf_counter()-t0)/(len(x)/B)*1000
            newon=[]; oldgone=[]; wrong=0
            for k,(tm,note) in enumerate(marks):
                if note is None or k==1: continue
                on=[e for e in ev if e[1]=='on' and e[0]>=tm-0.001]
                if on: newon.append(round((on[0][0]-tm)*1000)); wrong+= on[0][2]!=note
                gone=[e for e in ev if e[1] in ('on','choke','off') and e[0]>=tm-0.001]
                if gone: oldgone.append(round((gone[0][0]-tm)*1000))
            print(f"{label:20s} {nm:6s} stick {stick}: new note after {int(np.median(newon))} ms (max {max(newon)}), old note silenced after {int(np.median(oldgone))} ms, wrong notes {wrong}, cpu {cpu:.3f} ms per 0.7 ms block")
