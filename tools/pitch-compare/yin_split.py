"""On the real takes: split app-YIN's misses vs the consensus into 'pitch wrong' and 'pitch right but gated unvoiced'."""
import lowprio  # noqa: F401
import glob, os, json
import numpy as np
from real_compare import grid
tot = gated = wrong = 0
for f in sorted(glob.glob("real/*.wav")):
    T, S, cons, agree, uv, both = grid("out/real", os.path.basename(f)[:-4])
    for m in ["yin_app"]:
        s = S[m]; e = np.abs(s["c"] - cons)
        tot += agree.sum()
        gated += (agree & ~s["voiced"] & (e <= 50)).sum()
        wrong += (agree & ~(e <= 50)).sum()
r = dict(consensus_frames=int(tot), gated_but_pitch_right=gated / tot, pitch_wrong=wrong / tot)
print(r); json.dump(r, open("yin_split_real.json", "w"), indent=1)
