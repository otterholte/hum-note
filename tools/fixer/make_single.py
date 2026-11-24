"""Builds one self-contained HTML file (audio embedded) of the note fixer, for sending straight to a phone."""
import base64, glob, json, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
s = open('index.html', encoding='utf-8').read()
b64 = lambda f: base64.b64encode(open(f, 'rb').read()).decode()
files = {'take.mp3': b64('take.mp3')}
for f in glob.glob(os.path.join('p', '*.mp3')):
    files['p/' + os.path.basename(f)] = b64(f)
old = "async function loadBuf(url){ const r=await fetch(url); if(!r.ok) throw new Error(url); return await audio().decodeAudioData(await r.arrayBuffer()); }"
new = ("async function loadBuf(url){ if(typeof EMBED!=='undefined'&&EMBED[url]){ const bin=atob(EMBED[url]), u=new Uint8Array(bin.length); "
       "for(let i=0;i<bin.length;i++) u[i]=bin.charCodeAt(i); return await audio().decodeAudioData(u.buffer); } "
       "const r=await fetch(url); if(!r.ok) throw new Error(url); return await audio().decodeAudioData(await r.arrayBuffer()); }")
assert old in s
s = s.replace(old, new, 1).replace('<script>\n', '<script>\nconst EMBED=' + json.dumps(files) + ';\n', 1)
out = ('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
       '</head><body>' + s + '</body></html>')
open('Note Fixer 01-58-26.html', 'w', encoding='utf-8').write(out)
print(round(len(out) / 1e6, 2), 'MB')
