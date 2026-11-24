"""One MP3 per clip: the original 10 s, a short pause, Humnote's notes on the upright piano, a pause, then both together."""
import json, os, sys, subprocess, importlib.util, numpy as np, soundfile as sf, imageio_ffmpeg
HERE = os.path.dirname(os.path.abspath(__file__)); FF = imageio_ffmpeg.get_ffmpeg_exe()
spec = importlib.util.spec_from_file_location('rp', os.path.join(HERE, '..', 'render', 'render_piano.py')); rp = importlib.util.module_from_spec(spec); spec.loader.exec_module(rp)
SR = rp.SR; OUT = os.path.join(HERE, '..', '..', 'demo-audio', 'listen-test'); os.makedirs(OUT, exist_ok=True)
idx = json.load(open(os.path.join(HERE, 'clips', 'index.json')))
for name in idx:
    y, fs = sf.read(os.path.join(HERE, 'clips', name + '.wav'), dtype='float32')
    if fs != SR: y = np.interp(np.arange(int(len(y) * SR / fs)) * fs / SR, np.arange(len(y)), y)
    y = y / (np.abs(y).max() + 1e-9) * 0.8; n = len(y)
    d = json.load(open(os.path.join(HERE, 'out', name + '.json')))
    pn = np.zeros((n + SR * 2, 2))
    for o in d['notes']:
        v = rp.voice(o['pitch'], o.get('vel', 90), o['end'] - o['start']); a = int(o['start'] * SR); b = min(len(pn), a + len(v)); pn[a:b] += v[:b - a]
    pn = pn[:n + SR]; pn *= 0.8 / (np.abs(pn).max() + 1e-9)
    gap = np.zeros((int(0.9 * SR), 2)); orig = np.stack([y, y], 1)
    both = np.pad(orig, ((0, len(pn) - n), (0, 0))) * 0.85 + pn * 0.6
    mix = np.concatenate([orig, gap, pn, gap, both]); mix *= 0.9 / np.abs(mix).max()
    out = os.path.join(OUT, name + '.mp3')
    subprocess.run([FF, '-y', '-loglevel', 'error', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', '-', '-b:a', '160k', out], input=mix.astype(np.float32).tobytes(), check=True)
    print('wrote', os.path.basename(out))
