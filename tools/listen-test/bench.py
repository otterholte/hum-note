"""Benchmark set: every VocalSet singer's "Row, Row, Row Your Boat" (straight + vibrato), first 10 s.
Writes bench/<name>.wav and bench/index.json (reference melody). Re-run safe."""
import os, json, subprocess, numpy as np, soundfile as sf, imageio_ffmpeg
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "bench"); os.makedirs(OUT, exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe(); FS = 48000
VS = r"S:\Coding Projects\Halo\ai\data\data_by_singer"
ROW = [60,60,60,62,64, 64,62,64,65,67, 72,72,72,67,67,67,64,64,64,60,60,60, 67,65,64,62,60]
idx = {}
for sid in sorted(os.listdir(VS)):
    for style in ("straight", "vibrato"):
        d = os.path.join(VS, sid, "excerpts", style)
        if not os.path.isdir(d): continue
        for f in os.listdir(d):
            if "_row_" not in f: continue
            name = f"{sid} {style}"
            raw = subprocess.run([FF, "-loglevel", "error", "-t", "10", "-i", os.path.join(d, f), "-ac", "1", "-ar", str(FS), "-f", "f32le", "-"], capture_output=True, check=True).stdout
            y = np.frombuffer(raw, np.float32); y = y / (np.abs(y).max() + 1e-9) * 0.7
            sf.write(os.path.join(OUT, name + ".wav"), y, FS, subtype="PCM_16"); idx[name] = dict(kind="real", ref=ROW, source=f"VocalSet {sid} (CC BY 4.0)")
json.dump(idx, open(os.path.join(OUT, "index.json"), "w"), indent=1); print(len(idx), "clips")
