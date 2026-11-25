import sys, numpy as np, importlib.util
from scipy.signal import butter, sosfilt
sys.path.insert(0, r"S:\Coding Projects\HumToMidi\tools\listen-test"); import live_replay as R
def render(path, snd, take, key, stick=1.0):
    spec=importlib.util.spec_from_file_location("eng",path); L=importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
    x,sr=R.read(f"S:/Coding Projects/HumToMidi/recordings/{take}.wav"); x=x/abs(x).max()*0.3
    osr=96000; up=np.interp(np.arange(int(len(x)*osr/sr))*sr/osr, np.arange(len(x)), x).astype(np.float32)
    A=L.Analyzer(osr//2); A.stick=stick; A.allowed=set(key); S=L.Synth(osr); S.snd=snd; B=64; out=[]
    for i in range(0,len(up)-B,B):
        y=up[i:i+B]; y=0.5*(y[0::2]+y[1::2])
        for e in A.feed(y):
            if e[0]=='on': S.on(e[1],e[2])
            elif e[0]=='choke': S.choke=True
            elif e[0]=='unchoke': S.choke=False
            else: S.off()
        S.tone=A.tone; out.append(S.render(B))
    return np.concatenate(out), osr
sos=butter(6, 5000, 'highpass', fs=96000, output='sos')
for take,key in (("hum_2026-11-24_235532",[5,7,9,10,0,2,4]),("hum_2026-11-24_235350",[2,4,6,7,9,11,1])):
    for snd in ("keys","pluck"):
        row=[]
        for name,path in (("before",sys.argv[1]),("now",sys.argv[2])):
            o,sr=render(path,snd,take,key); h=sosfilt(sos,o); w=int(0.002*sr); n=len(h)//w
            e=np.sqrt((h[:n*w].reshape(n,w)**2).mean(1)); full=np.sqrt((o**2).mean())
            row.append(f"{name}: {int((e>0.01*full*3).sum()):3d} bursts, loudest {20*np.log10(e.max()/full+1e-12):.0f} dB")
        print(take[-6:], snd.ljust(5), ' | '.join(row))
