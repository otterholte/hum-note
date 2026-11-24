import json, sys, numpy as np, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
d = json.load(open(sys.argv[1])); t = d["t0"] + np.arange(len(d["m"])) * d["dt"]; m = np.array(d["m"]); mv = np.array(d["mv"]); v = np.array(d["voiced"]) > 0; c = np.array(d["curve"]); vb = np.array(d["vib"]) > 0
fig, ax = plt.subplots(figsize=(16, 5)); ax.plot(t[v], (m - c)[v], ".", ms=2, color="0.6", label="pitch"); ax.plot(t[v & vb], (mv - c)[v & vb], ".", ms=2, color="tab:blue", label="vibrato centre (detected)")
for n in d["notes"]: ax.plot([n["start"], n["end"]], [n["pitch"]] * 2, color="tab:red", lw=5, alpha=.55)
lo, hi = int(np.nanmin((m - c)[v])) - 1, int(np.nanmax((m - c)[v])) + 2; N = ['C','Db','D','Eb','E','F','Gb','G','Ab','A','Bb','B']
ax.set_yticks(range(lo, hi)); ax.set_yticklabels([N[p % 12] + str(p // 12 - 1) for p in range(lo, hi)]); ax.set_ylim(lo, hi - 1); ax.grid(axis="y", alpha=.3); ax.legend(loc="upper left"); ax.set_title(sys.argv[3])
fig.tight_layout(); fig.savefig(sys.argv[2], dpi=80)
