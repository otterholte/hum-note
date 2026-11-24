"""Builds two HumTrans test sets (humming with correct MIDI notes; CC BY-NC 4.0, kept local, never committed).
  ht   = 40 clips from the VALID split (to tune on)      htx = 40 clips from the TEST split (held back, to check)
usage: python make_humtrans.py [N]   (pulls only the chosen clips out of the 14.7 GB zip)"""
import os, sys, json, random, zipfile, io
import numpy as np, soundfile as sf, mido
from remotezip import RemoteZip
HERE = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(HERE, "humtrans_src"); N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
keys = json.load(open(os.path.join(SRC, "keys.json"))); mz = zipfile.ZipFile(os.path.join(SRC, "all_midi.zip"))
wz = RemoteZip("https://huggingface.co/datasets/dadinghh2/HumTrans/resolve/main/all_wav.zip")
def notes(mid):
    m = mido.MidiFile(file=io.BytesIO(mz.read("midi_data/" + mid + ".mid"))); t = 0; on = {}; out = []
    for msg in m:
        t += msg.time
        if msg.type == "note_on" and msg.velocity > 0: on[msg.note] = t
        elif msg.type in ("note_off", "note_on") and msg.note in on: out.append((on.pop(msg.note), t, msg.note))
    return sorted(out)
for setname, split in (("ht", "VALID"), ("htx", "TEST")):
    out = os.path.join(HERE, setname); os.makedirs(out, exist_ok=True); idx = {}
    pick = random.Random(7).sample(sorted(keys[split]), N)
    for k in pick:
        ns = notes(k); dst = os.path.join(out, k + ".wav")
        if not os.path.exists(dst):
            y, sr = sf.read(io.BytesIO(wz.read("wav_data_sync_with_midi/" + k + ".wav")), dtype="float32")
            if y.ndim > 1: y = y.mean(1)
            sf.write(dst, y / (np.abs(y).max() + 1e-9) * 0.7, sr, subtype="PCM_16")
        idx[k] = dict(kind="hum", ref=[n[2] for n in ns], times=[[round(a, 3), round(b, 3)] for a, b, _ in ns], source="HumTrans (CC BY-NC 4.0)")
    json.dump(idx, open(os.path.join(out, "index.json"), "w"), indent=0); print(setname, len(idx))
