# How well a note list matches what was actually sung (SwiftF0 pitch, A440): per note, the sung median vs the note.
import json, sys, numpy as np
t, m = np.load(sys.argv[1]); notes = json.load(open(sys.argv[2]))["notes"]; label = sys.argv[3]
offs = []; bad = 0; tot = 0
for n in notes:
    sel = (t >= n["start"]) & (t < n["end"]) & ~np.isnan(m)
    if sel.sum() < 3: continue
    md = np.median(m[sel]); offs.append(md - n["pitch"]); tot += 1
offs = np.array(offs); g = np.median(offs)  # the singer's overall tuning offset
far = np.abs(offs - g) > 0.5
print(f"{label:<28} notes {tot:3d}  overall offset {100*g:+5.0f}c  notes more than half a semitone off what you sang: {far.sum():2d} ({100*far.mean():.0f}%)  avg miss {100*np.mean(np.abs(offs-g)):.0f}c")
