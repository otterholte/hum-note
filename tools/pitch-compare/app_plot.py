import json, sys, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
d = json.load(open(sys.argv[1])); t = d["t0"] + np.arange(len(d["m"])) * d["dt"]; m = np.array(d["m"]); v = np.array(d["voiced"]) > 0; c = np.array(d["curve"])
names = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']; nm = lambda p: names[int(p) % 12] + str(int(p) // 12 - 1)
fig, ax = plt.subplots(figsize=(16, 5)); ax.plot(t[v], (m - c)[v], ".", ms=2, color="k")
for n in d["notes"]: ax.plot([n["start"], n["end"]], [n["pitch"]] * 2, color="tab:red", lw=5, alpha=.55)
lo, hi = int(np.nanmin((m - c)[v])) - 1, int(np.nanmax((m - c)[v])) + 2; ax.set_yticks(range(lo, hi)); ax.set_yticklabels([nm(p) for p in range(lo, hi)]); ax.set_ylim(lo, hi - 1); ax.grid(axis="y", alpha=.35)
ax.set_title(sys.argv[3] if len(sys.argv) > 3 else "dots = your voice on the app's tuning grid, red = notes"); fig.tight_layout(); fig.savefig(sys.argv[2], dpi=85)
