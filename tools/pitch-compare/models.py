"""Neural pitch trackers behind one interface.

Each runner takes mono float32 audio at 16 kHz (peak-normalised to 0.9, like the app does)
and returns dict(t=seconds, f0=Hz, conf=0..1 or None, voiced=bool) at the model's native hop.
"""
import os, sys
import lowprio  # noqa: F401
import numpy as np
import torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "pylib"))               # pesto-pitch, swift-f0 (installed with --target)
APPLIO = r"S:\Coding Projects\Halo\ai\applio"                  # RMVPE source + checkpoints (Applio, MIT)
SR = 16000

_cache = {}


def _crepe(size):
    import torchcrepe

    def run(x, device):
        a = torch.from_numpy(x)[None].to(device)
        with torch.inference_mode():
            f0, per = torchcrepe.predict(a, SR, hop_length=160, fmin=50, fmax=1100, model=size,
                                         decoder=torchcrepe.decode.weighted_argmax, return_periodicity=True,
                                         batch_size=64, device=device, pad=True)
        f0 = f0[0].cpu().numpy().astype(np.float64); per = per[0].cpu().numpy().astype(np.float64)
        return dict(t=np.arange(len(f0)) * 0.01, f0=f0, conf=per, voiced=per >= 0.5)
    return run


def _swift():
    from swift_f0 import SwiftF0

    def run(x, device):
        key = ("swift", torch.get_num_threads())
        if key not in _cache:
            _cache[key] = SwiftF0(threads=torch.get_num_threads(), spin=False)
        r = _cache[key].detect(x, SR, fmin=46.875, fmax=2093.75)
        return dict(t=np.asarray(r.timestamps), f0=np.asarray(r.pitch_hz, float), conf=np.asarray(r.confidence, float),
                    voiced=np.asarray(r.confidence) >= 0.5)
    return run


def _pesto(name):
    import pesto
    from pesto.loader import load_model

    def run(x, device):
        key = ("pesto", name, device)
        if key not in _cache:
            m = load_model(name, 10.0, sampling_rate=SR).to(device)
            _cache[key] = m
        m = _cache[key]
        a = torch.from_numpy(x).to(device)
        with torch.inference_mode():
            ts, p, c, _ = pesto.core._predict(a, SR, m, num_chunks=1, convert_to_freq=True)
        f0 = p.cpu().numpy().astype(np.float64).reshape(-1); c = c.cpu().numpy().astype(np.float64).reshape(-1)
        t = ts.cpu().numpy().astype(np.float64) / 1000.0
        return dict(t=t, f0=f0, conf=c, voiced=c >= 0.5)
    return run


def _rmvpe():
    if APPLIO not in sys.path:
        sys.path.insert(0, APPLIO)
    from rvc.lib.predictors.RMVPE import RMVPE0Predictor

    def run(x, device):
        key = ("rmvpe", device)
        if key not in _cache:
            _cache[key] = RMVPE0Predictor(os.path.join(APPLIO, "rvc", "models", "predictors", "rmvpe.pt"), device=device)
        p = _cache[key]
        with torch.inference_mode():
            a = torch.from_numpy(x).float().to(device)[None]
            mel = p.mel_extractor(a, center=True)
            hidden = p.mel2hidden(mel).squeeze(0).cpu().numpy()
        f0 = p.decode(hidden, thred=0.03)
        conf = hidden.max(axis=1)
        return dict(t=np.arange(len(f0)) * 0.01, f0=np.where(f0 > 0, f0, np.nan), conf=conf.astype(float), voiced=f0 > 0)
    return run


def _fcpe():
    from torchfcpe import spawn_bundled_infer_model

    def run(x, device):
        key = ("fcpe", device)
        if key not in _cache:
            _cache[key] = spawn_bundled_infer_model(device=device)
        m = _cache[key]
        a = torch.from_numpy(x).float().to(device)[None, :, None]
        with torch.inference_mode():
            f0 = m.infer(a, sr=SR, decoder_mode="local_argmax", threshold=0.006, f0_min=50, f0_max=1100,
                         interp_uv=False).squeeze().cpu().numpy().astype(np.float64)
        return dict(t=np.arange(len(f0)) * 0.01, f0=np.where(f0 > 0, f0, np.nan), conf=None, voiced=f0 > 50)
    return run


MODELS = {
    "crepe_tiny": _crepe("tiny"),
    "crepe_full": _crepe("full"),
    "swiftf0": _swift(),
    "pesto": _pesto("mir-1k_g7"),
    "rmvpe": _rmvpe(),
    "fcpe": _fcpe(),
}


def load_audio(path):
    import soundfile as sf, soxr
    x, sr = sf.read(path, dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr != SR:
        x = soxr.resample(x, sr, SR).astype(np.float32)
    x = x * (0.9 / (np.abs(x).max() + 1e-9))
    return x.astype(np.float32)
