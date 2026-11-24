# Pitch of one take (SwiftF0) vs the notes the app detected: per-note median sung pitch, and a plot.
import lowprio, sys, json, os, numpy as np
from models import MODELS, load_audio
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
wav = sys.argv[1]; j = json.load(open(wav[:-4] + ".json")); det = j.get("detected") or j["notes"]
x = load_audio(wav); r = MODELS["swiftf0"](x, "cpu"); t, f, v = r["t"], r["f0"], r["voiced"]
m = np.where(v, 69 + 12 * np.log2(np.maximum(f, 1) / 440), np.nan)
np.save(os.path.splitext(os.path.basename(wav))[0] + "_swift.npy", np.vstack([t, m]))
names = ['C','D♭','D','E♭','E','F','G♭','G','A♭','A','B♭','B']; nm = lambda p: names[int(p) % 12] + str(int(p) // 12 - 1)
print("note(app)  start  dur   sung(median)  -> nearest   off(c)")
for n in det:
    sel = (t >= n["start"]) & (t < n["end"]) & ~np.isnan(m)
    if sel.sum() < 2: print(f"{n['note']:<9} {n['start']:5.2f} {n['end']-n['start']:4.2f}   (no pitch)"); continue
    md = np.median(m[sel]); near = round(md); flag = "" if near == n["midi"] else "  <-- WRONG"
    print(f"{n['note']:<9} {n['start']:5.2f} {n['end']-n['start']:4.2f}   {md:6.2f}        {nm(near):<5}  {100*(md-near):+5.0f}{flag}")
fig, ax = plt.subplots(figsize=(16, 5)); ax.plot(t, m, ".", ms=2, color="k", label="sung (SwiftF0)")
for n in det: ax.plot([n["start"], n["end"]], [n["midi"]] * 2, color="tab:red", lw=4, alpha=.6)
ax.set_yticks(range(int(np.nanmin(m)) - 1, int(np.nanmax(m)) + 2)); ax.set_yticklabels([nm(p) for p in ax.get_yticks()]); ax.grid(axis="y", alpha=.3); ax.set_xlabel("s")
ax.set_title("red = notes the app detected, dots = what you sang"); fig.tight_layout(); fig.savefig(os.path.splitext(os.path.basename(wav))[0] + "_check.png", dpi=90)
