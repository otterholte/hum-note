import sys,json; sys.path.insert(0,__import__('os').path.dirname(__file__))
take=sys.argv[1]; key=[int(v) for v in sys.argv[2].split(',')]; stick=float(sys.argv[3]) if len(sys.argv)>3 else 0.5
sys.argv=['x']; import live_replay as R
x,sr=R.read(f'recordings/{take}.wav'); x=x/abs(x).max()*0.3
r,ev=R.run(x,sr,stick,key)
N=['C','Db','D','Eb','E','F','F#','G','Ab','A','Bb','B']
live=[(e[0],N[e[2]%12]+str(e[2]//12-1),e[2]) for e in ev if e[1]=='on']
J=json.load(open(f'recordings/{take}.json')); right=0; extra=0
for n in J['notes']:
    inside=[(t,nm,mi) for t,nm,mi in live if n['start']-0.05<=t<n['end']-0.05]
    nm=n['note'].replace('266d','b').replace('♭','b'); ok=any(mi==n['midi'] for _,_,mi in inside); first_ok=bool(inside) and inside[0][2]==n['midi']; firsts=globals().setdefault('F',[0]); firsts[0]+=first_ok; right+=ok; extra+=max(0,len(inside)-1)
    print(f"{n['start']:6.2f} {n['note']:4s} {'ok ' if ok else 'MISS'} | {' '.join(f'{t:.2f}:{v}' for t,v,_ in inside)}")
print('notes heard right',right,'/',len(J['notes']),' first sound right',F[0],' extra note starts',extra)
