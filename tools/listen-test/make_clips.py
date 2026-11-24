"""Builds the listening test: 10 s clips with known melodies.
 - synthetic amateur takes of public-domain tunes (pitch drift, ±30 cent misses, scoops, vibrato, loose timing)
 - real singers: VocalSet (CC BY 4.0) "Row, Row, Row Your Boat" excerpts, plus two Wikimedia Commons recordings
Writes clips/<name>.wav (48 kHz mono) and clips/index.json with each clip's reference melody (MIDI, intended notes).
"""
import os, sys, json, subprocess, numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "clips"); os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(HERE, "..", "pitch-compare"))
import synth  # the comparison's sung-voice synthesizer (formant vowels, scoops, vibrato, breaths)
FS = 48000

def tune(notes, start_midi, beat, drift=0.0, miss=30, vowel="a", rng=None, phrase_breaks=()):
    """notes: (scale offset in semitones, beats). Drift: semitones gained (sharp) by the end. Returns spec + reference."""
    total = sum(b for _, b in notes); t = 0; phr = [[]]; ref = []
    for i, (off, b) in enumerate(notes):
        intended = start_midi + off; ref.append(intended)
        sung = intended + drift * (t / total) + rng.uniform(-1, 1) * miss / 100      # amateur: drifts and misses a little
        dur = beat * b * rng.uniform(0.9, 1.1)                                     # loose timing
        phr[-1].append((sung, dur, vowel if vowel != "mix" else "aeo"[i % 3]))
        t += b
        if i + 1 in phrase_breaks: phr.append([])
    return dict(phrases=[p for p in phr if p], opt=dict(detune_c=0, gap=(0.25, 0.45), scoop=(0.05, 0.12), artic_db=(9 if vowel=="m" else 14))), ref

rng = np.random.default_rng(7)
clips = {}
# ---- synthetic amateur takes (intended melody known exactly)
T = [(0,1),(0,1),(7,1),(7,1),(9,1),(9,1),(7,2),(5,1),(5,1),(4,1),(4,1),(2,1),(2,1),(0,2)]                      # Twinkle Twinkle
O = [(4,1),(4,1),(5,1),(7,1),(7,1),(5,1),(4,1),(2,1),(0,1),(0,1),(2,1),(4,1),(4,1.5),(2,.5),(2,2)]             # Ode to Joy
H = [(-5,.75),(-5,.25),(-3,1),(-5,1),(0,1),(-1,2),(-5,.75),(-5,.25),(-3,1),(-5,1),(2,1),(0,2)]                 # Happy Birthday
F = [(0,1),(2,1),(4,1),(0,1),(0,1),(2,1),(4,1),(0,1),(4,1),(5,1),(7,2),(4,1),(5,1),(7,2)]                      # Frère Jacques
for name, notes, start, beat, drift, miss, vowel, br, opt in [
    ("synth 1 - Twinkle Twinkle (hummed, low voice, drifts sharp)", T, 48, 0.52, +0.6, 30, "m", (7,), {}),
    ("synth 2 - Ode to Joy (la-la, drifts flat, loose)", O, 50, 0.5, -0.45, 35, "a", (8,), {}),
    ("synth 3 - Happy Birthday (higher voice, vibrato)", H, 65, 0.62, +0.3, 25, "mix", (6,), dict(vib_pp=(1.2, 2.0))),
    ("synth 4 - Frere Jacques (quick, breathy, noisy room)", F, 53, 0.4, +0.25, 30, "o", (4, 8, 11), dict(hnr_db=14, snr_db=22)),
]:
    spec, ref = tune(notes, start, beat, drift, miss, vowel, rng, br); spec["opt"].update(opt)
    y, _ = synth.make_clip(spec, np.random.default_rng(len(clips) + 11)); y = y[:FS * 10]
    sf.write(os.path.join(OUT, name + ".wav"), y, FS, subtype="PCM_16"); clips[name] = dict(kind="synthetic", ref=ref)

# ---- real singers
ROW = [60,60,60,62,64, 64,62,64,65,67, 72,72,72,67,67,67,64,64,64,60,60,60, 67,65,64,62,60]                     # Row, Row, Row Your Boat (in C)
VS = r"S:\Coding Projects\Halo\ai\data\data_by_singer"
ff = None
try:
    import imageio_ffmpeg; ff = imageio_ffmpeg.get_ffmpeg_exe()
except Exception: pass
def cut(src, dst, start=0.0):
    raw = subprocess.run([ff, "-loglevel", "error", "-ss", str(start), "-t", "10", "-i", src, "-ac", "1", "-ar", str(FS), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    y = np.frombuffer(raw, np.float32); y = y / (np.abs(y).max() + 1e-9) * 0.7; sf.write(dst, y, FS, subtype="PCM_16")
for sid, style, label in [("female2", "straight", "woman, straight"), ("male3", "straight", "man, straight"), ("female5", "vibrato", "woman, vibrato"), ("male5", "vibrato", "man, vibrato")]:
    src = os.path.join(VS, sid, "excerpts", style, f"{sid[0]}{sid[-1] if sid[-2].isalpha() else sid[-2:]}_row_{style}.wav")
    if not os.path.exists(src):
        cands = [f for f in os.listdir(os.path.join(VS, sid, "excerpts", style)) if "_row_" in f]; src = os.path.join(VS, sid, "excerpts", style, cands[0])
    name = f"real {len(clips)-3} - Row Row Row Your Boat (VocalSet {sid}, {label})"
    cut(src, os.path.join(OUT, name + ".wav")); clips[name] = dict(kind="real", ref=ROW, source=f"VocalSet {sid} (CC BY 4.0)")
V = os.environ.get("VOCALS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources"))  # the downloaded .ogg songs
for fn, name, src in [("Scarborough_Fair.ogg", "real 5 - Scarborough Fair (Wikimedia Commons)", "User:Makemi, Wikimedia Commons, CC BY-SA 3.0"),
                      ("Danny_Boy_-_Tom_Evans.ogg", "real 6 - Danny Boy (Tom Evans, Wikimedia Commons)", "Tom Evans, Wikimedia Commons")]:
    cut(os.path.join(V, fn), os.path.join(OUT, name + ".wav")); clips[name] = dict(kind="real", ref=None, source=src)
json.dump(clips, open(os.path.join(OUT, "index.json"), "w"), indent=1)
print("\n".join(clips))
