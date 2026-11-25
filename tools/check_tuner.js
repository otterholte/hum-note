// Guard: the tuner's colours are fixed by the user's request — green within ±20 cents, yellow 20-40, red beyond.
// Run after any edit: node tools/check_tuner.js   (exits 1 if something changed them)
const fs = require('fs'), path = require('path'); const H = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const ok = [
  ['tolerance forced to 20 after loading settings', /st\.tol=20;/.test(H)],
  ['no Tolerance buttons', !/id="segTol"/.test(H)],
  ['saved settings never restore tol', !/'ts','tol'/.test(H)],
  ['green/yellow limits exact (20 / 40)', /okLim=T, farLim=2\*T/.test(H)],
  ['default tol is 20', /tol:20/.test(H)],
];
let bad = 0; for (const [name, pass] of ok) { console.log((pass ? 'ok   ' : 'FAIL ') + name); if (!pass) bad++; }
process.exit(bad ? 1 : 0);
