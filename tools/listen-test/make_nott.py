"""Nottingham folk tunes (melody + chords) -> nott.json for learning and testing the chord picker.
Keeps simple meters counted in quarter notes (2/4, 3/4, 4/4); each tune: meter, key (tonic, mode), melody and chords in beats."""
import zipfile, io, json, mido
z = zipfile.ZipFile("nottingham_src/nott.zip"); out = {}
TEMPL = {"": [0, 4, 7], "m": [0, 3, 7], "dim": [0, 3, 6], "7": [0, 4, 7, 10], "m7": [0, 3, 7, 10]}
KEYS = {k: i for i, k in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}; KEYS.update({"Db": 1, "Eb": 3, "Gb": 6, "Ab": 8, "Bb": 10, "Cb": 11})
def chord_of(ps):
    pcs = set(p % 12 for p in ps); best = None
    for r in range(12):
        for q, iv in TEMPL.items():
            t = set((r + i) % 12 for i in iv); sc = len(t & pcs) - 0.6 * len(pcs - t) - 0.3 * len(t - pcs) + (0.1 if r == min(ps) % 12 else 0)
            if not best or sc > best[0]: best = (sc, r, q)
    return best[1], best[2]
for name in sorted(x for x in z.namelist() if x.endswith(".mid")):
    try: m = mido.MidiFile(file=io.BytesIO(z.read(name)))
    except Exception: continue
    tpb = m.ticks_per_beat; ts = None; key = None; tracks = []
    for t in m.tracks:
        tick = 0; on = {}; notes = []
        for x in t:
            tick += x.time
            if x.type == "time_signature" and ts is None: ts = (x.numerator, x.denominator)
            if x.type == "key_signature" and key is None: key = x.key
            if x.type == "note_on" and x.velocity > 0: on.setdefault(x.note, tick)
            elif x.type in ("note_off", "note_on") and x.note in on: notes.append((on.pop(x.note) / tpb, tick / tpb, x.note))
        tracks.append(sorted(notes))
    if not ts or ts[1] != 4 or ts[0] not in (2, 3, 4) or len(tracks) < 2 or not key: continue
    mel, ch = tracks[0], tracks[1]
    if len(mel) < 16 or not ch: continue
    groups = {}
    for s, e, p in ch: groups.setdefault((s, e), []).append(p)
    chords = [[s, e, *chord_of(ps)] for (s, e), ps in sorted(groups.items())]
    minor = key.endswith("m"); tonic = KEYS[key[:-1] if minor else key]
    out[name.split("/")[-1][:-4]] = dict(meter=ts[0], tonic=tonic, minor=minor, mel=[[round(s, 3), round(e, 3), p] for s, e, p in mel], chords=chords)
json.dump(out, open("nott.json", "w")); print("tunes", len(out), "minor", sum(v["minor"] for v in out.values()), {m: sum(v["meter"] == m for v in out.values()) for m in (2, 3, 4)})
