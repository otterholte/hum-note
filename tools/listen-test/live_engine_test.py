import sys, time, math, numpy as np
sys.path.insert(0, r"S:\Coding Projects\HumToMidi")
from live_engine import Analyzer, Synth
sr=48000
def voice(seq):
    out=[]; ph=0; marks=[]; t=0
    for (m0,m1,d,a) in seq:
        n=int(sr*d); m=np.linspace(m0,m1,n)+0.25*np.sin(2*np.pi*5.5*(t+np.arange(n)/sr))*(1 if a>0 else 0)
        f=440*2**((m-69)/12); p=ph+2*np.pi*np.cumsum(f)/sr; ph=p[-1]
        x=sum((0.5/k)*np.sin(k*p) for k in range(1,10))*a*0.1
        marks.append((t,m1 if a>0 else None)); out.append(x); t+=d
    y=np.concatenate(out).astype(np.float32); return y+np.random.randn(len(y)).astype(np.float32)*0.0005, marks
# G major riff with a scoop, a flat note, a repeated syllable, vibrato everywhere
seq=[(0,0,0.3,0),(55,55,0.4,1),(59,59,0.3,1),(61.6,62,0.05,1),(62,62,0.35,1),(67,67,0.4,1),(64.35,64.35,0.3,1),(64,64,0.02,0.2),(64,64,0.3,1),(62,62,0.3,1),(0,0,0.15,0),(60,60,0.3,1),(59,59,0.3,1),(55,55,0.5,1),(0,0,0.3,0)]
x,marks=voice(seq)
for allowed,stick in [(range(12),0.5),([7,9,11,0,2,4,6],0.5),([7,9,11,0,2,4,6],0.1),([7,9,11,0,2,4,6],0.9)]:
    A=Analyzer(sr); A.allowed=set(allowed); A.stick=stick; B=144; ev=[]; t0=time.perf_counter()
    for i in range(0,len(x)-B,B):
        for e in A.feed(x[i:i+B]): ev.append((round((i+B)/sr,3),)+e[:2])
    cpu=(time.perf_counter()-t0)/(len(x)/B)*1000
    print(f"allowed={'all' if len(list(allowed))==12 else 'G maj'} stick={stick}  cpu/block={cpu:.2f}ms (block={B/sr*1000:.1f}ms)")
    print("  events:", [(t,e,n) for t,e,n in [(a[0],a[1],a[2] if len(a)>2 else '') for a in ev]])
    # delay from each sung-note start to the next 'on'
    lat=[]
    for (tm,note) in marks:
        if note is None: continue
        nx=[a for a in ev if a[1]=='on' and a[0]>=tm-0.001]
        if nx: lat.append(round((nx[0][0]-tm)*1000))
    print("  ms from note start to note-on:", lat)
S=Synth(sr); S.on(60,0.8); t0=time.perf_counter()
for i in range(300): y=S.render(144)
print("synth cpu/block %.2f ms"%((time.perf_counter()-t0)/300*1000), float(np.abs(y).max()))
