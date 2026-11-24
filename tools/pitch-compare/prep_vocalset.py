"""Copy 10 short VocalSet excerpts (CC BY 4.0, Wilkins et al. 2018) into vocalset/ (first 8 s each)."""
import lowprio  # noqa: F401
import os, glob
import soundfile as sf
SRC = r"S:\Coding Projects\Halo\ai\data\data_by_technique"
PICK = [("vibrato", "m2"), ("vibrato", "f3"), ("fast_forte", "m4"), ("fast_forte", "f5"), ("breathy", "m6"),
        ("breathy", "f2"), ("straight", "m8"), ("pp", "f6"), ("slow_piano", "m3"), ("belt", "f1")]
os.makedirs("vocalset", exist_ok=True)
for tech, singer in PICK:
    fs = sorted(f for f in glob.glob(os.path.join(SRC, tech, "*.wav")) if os.path.basename(f).startswith(singer + "_"))
    fs = [f for f in fs if "arpeggio" in f or "scale" in f] or fs
    x, sr = sf.read(fs[0], dtype="float32")
    if x.ndim > 1: x = x.mean(1)
    out = os.path.join("vocalset", os.path.basename(fs[0]))
    sf.write(out, x[: 8 * sr], sr)
    print(out, sr)
