# Replay a real take through the live engine, as if sung live; report chopping.
import sys, wave, numpy as np
sys.path.insert(0, r"S:\Coding Projects\HumToMidi"); import live_engine as L
def read(p):
    w=wave.open(p); sr=w.getframerate(); n=w.getnframes(); ch=w.getnchannels(); sw=w.getsampwidth(); b=w.readframes(n)
    x=np.frombuffer(b,dtype={2:np.int16,4:np.int32}[sw]).astype(np.float32)/(2**(8*sw-1)); x=x.reshape(-1,ch).mean(1); return x,sr
def run(x,sr,stick,allowed,verbose=False):
    A=L.Analyzer(sr); A.stick=stick; A.allowed=set(allowed); B=max(16,int(sr*0.0007)); ev=[]; voiced=0; silent_voiced=0; playing=False; choked=False; hop=0
    for i in range(0,len(x)-B,B):
        for e in A.feed(x[i:i+B]):
            ev.append((i/sr,)+e)
            if e[0]=='on': playing, choked = True, False
            elif e[0]=='off': playing=False
            elif e[0]=='choke': choked=True
            elif e[0]=='unchoke': choked=False
        v = A.midi==A.midi
        if v: voiced+=1; silent_voiced+= (not playing) or choked
    dur=len(x)/sr; c=lambda k: sum(1 for e in ev if e[1]==k)
    return dict(dur=round(dur,1), ons=c('on'), offs=c('off'), chokes=c('choke'), unchokes=c('unchoke'), silent_while_singing=f"{100*silent_voiced/max(1,voiced):.0f}%"), ev
for f in sys.argv[1:]:
    x,sr=read(f); x=x/ (np.abs(x).max()+1e-9)*0.3
    print(f, sr)
    key={'235532':[5,7,9,10,0,2,4],'235350':[2,4,6,7,9,11,1]}[[k for k in ('235532','235350') if k in f][0]]
    for name,al in (('in its key',key),('any note',range(12))):
        for stick in (0.0,0.5,1.0):
            r,ev=run(x,sr,stick,al); print('  ',name,'stick',stick,r)
