// Runs the app's OWN pitch code (from index.html, read-only) on WAV files and writes per-frame pitch.
//  - "yin_app":   Hum.frames(Hum.track(x,16000))  -> the transcription pitch track (YIN + voicing + octave repair + median-5)
//  - "yin_tuner": the live-tuner yin() from the second script, run every 10 ms on the newest 45 ms
//                 with the tuner's own voicing gate, octave snap and 5-value median (display smoothing excluded)
// usage: node yin_app.js out_dir file1.wav [file2.wav ...]
// Writes out_dir/<model>/<name>.json  {t:[], f0:[], voiced:[], ms_per_sec}
const fs = require('fs'), path = require('path'), vm = require('vm');
const html = fs.readFileSync(path.join(__dirname, '..', '..', 'index.html'), 'utf8');
const core = html.match(/<script id="core">([\s\S]*?)<\/script>/)[1];
const sb = { module: { exports: {} }, Math, Float64Array, Float32Array, Uint8Array, Int16Array, Array, Number, isNaN, Object, JSON, Map, Set, console };
vm.createContext(sb); vm.runInContext(core + ';module.exports=Hum;', sb); const Hum = sb.module.exports;
// the tuner's yin(), extracted verbatim
const yinSrc = html.match(/function yin\(x,sr\)\{[\s\S]*?\n  return \{f:sr\/t, ap:b, rms\}; \}/)[0];
const yin = new Function(yinSrc + ';return yin;')();

function readWav(f) { // same reader as tools/run.js
  const b = fs.readFileSync(f); let o = 12, sr = 0, ch = 1, bits = 16, data = null;
  while (o < b.length - 8) { const id = b.toString('ascii', o, o + 4), L = b.readUInt32LE(o + 4);
    if (id === 'fmt ') { ch = b.readUInt16LE(o + 10); sr = b.readUInt32LE(o + 12); bits = b.readUInt16LE(o + 22); }
    if (id === 'data') data = b.subarray(o + 8, o + 8 + L); o += 8 + L + (L & 1); }
  const n = data.length / (bits / 8) / ch, x = new Float32Array(n);
  for (let i = 0; i < n; i++) { let s = 0; for (let c = 0; c < ch; c++) s += bits === 16 ? data.readInt16LE((i * ch + c) * 2) / 32768 : bits === 24 ? (data.readIntLE((i * ch + c) * 3, 3) / 8388608) : data.readFloatLE((i * ch + c) * 4); x[i] = s / ch; }
  return { x, sr }; }
function resample(x, sr, to) { // same resampler as tools/run.js
  if (sr === to) return x; const r = to / sr, n = Math.ceil(x.length * r), y = new Float32Array(n), fc = Math.min(1, r) * 0.95, Z = 16;
  for (let i = 0; i < n; i++) { const t = i / r, c = Math.floor(t); let s = 0, w = 0; for (let k = c - Z / fc | 0; k <= c + Z / fc; k++) { if (k < 0 || k >= x.length) continue; const u = (t - k) * fc, sinc = u === 0 ? 1 : Math.sin(Math.PI * u) / (Math.PI * u), win = 0.5 + 0.5 * Math.cos(Math.PI * Math.min(1, Math.abs(t - k) * fc / Z)); const g = sinc * win; s += x[k] * g; w += g; } y[i] = w ? s / w : 0; }
  return y; }

function runApp(y) {
  const t0 = process.hrtime.bigint();
  const F = Hum.frames(Hum.track(y, 16000));
  const ms = Number(process.hrtime.bigint() - t0) / 1e6;
  const t = [], f0 = [], v = [];
  for (let i = 0; i < F.n; i++) { t.push(F.t0 + i * F.dt); f0.push(440 * 2 ** ((F.m[i] - 69) / 12)); v.push(F.voiced[i]); }
  return { t, f0, voiced: v, ms };
}
function runTuner(x, sr) {
  // mimic tunerLoop: ring buffer at device rate, take newest 45 ms, box-decimate to ~16 kHz, yin(), gate, octave snap, median of last 5
  const q = Math.max(1, Math.round(sr / 16000)), need = Math.round(sr * 0.045), hop = Math.round(sr * 0.01);
  let noise = 1e-3; const last = []; const t = [], f0 = [], v = [];
  let ms = 0;
  for (let w = need; w <= x.length; w += hop) {
    const t0 = process.hrtime.bigint();
    const xx = new Float32Array(Math.floor(need / q));
    for (let i = 0; i < xx.length; i++) { let s = 0; for (let k = 0; k < q; k++) s += x[w - need + i * q + k]; xx[i] = s / q; }
    const y = yin(xx, sr / q); noise = Math.min(noise * 1.002 + 1e-6, y ? Math.max(y.rms, 1e-5) : noise);
    let m = NaN; if (y && y.f && y.ap < 0.2 && y.rms > Math.max(0.006, noise * 4)) m = 69 + 12 * Math.log2(y.f / 440);
    if (!isNaN(m)) { if (last.length && Math.abs(m - last[last.length - 1]) > 9) m += 12 * Math.round((last[last.length - 1] - m) / 12); last.push(m); if (last.length > 5) last.shift(); m = [...last].sort((a, b) => a - b)[last.length >> 1]; } else last.length = 0;
    ms += Number(process.hrtime.bigint() - t0) / 1e6;
    // the window's newest sample is "now"; its centre lags by ~22 ms
    t.push((w - need / 2) / sr); f0.push(isNaN(m) ? (y && y.f ? y.f : 0) : 440 * 2 ** ((m - 69) / 12)); v.push(isNaN(m) ? 0 : 1);
  }
  return { t, f0, voiced: v, ms, per_frame_ms: ms / t.length };
}

const [, , outDir, ...files] = process.argv;
for (const m of ['yin_app', 'yin_tuner']) fs.mkdirSync(path.join(outDir, m), { recursive: true });
for (const f of files) {
  const name = path.basename(f, '.wav');
  const { x, sr } = readWav(f);
  const y = resample(x, sr, 16000);
  let pk = 0; for (const v of y) pk = Math.max(pk, Math.abs(v)); for (let i = 0; i < y.length; i++) y[i] *= 0.9 / pk; // as run.js
  const dur = y.length / 16000;
  const a = runApp(y); a.ms_per_sec = a.ms / dur;
  fs.writeFileSync(path.join(outDir, 'yin_app', name + '.json'), JSON.stringify(a));
  // tuner sees the raw device-rate stream (no normalisation), like the app
  const b = runTuner(x, sr); b.ms_per_sec = b.ms / dur;
  fs.writeFileSync(path.join(outDir, 'yin_tuner', name + '.json'), JSON.stringify(b));
  console.log(name, 'app', a.ms_per_sec.toFixed(1), 'ms/s', ' tuner', b.per_frame_ms.toFixed(3), 'ms/frame');
}
