// Runs the app's own transcription (as the page does) on a WAV and dumps frames, tuning grid and notes as JSON.
// node app_dump.js <index.html> <take.wav> <out.json> [keyStrength=1]
const fs=require('fs'); const [,,html,wavf,outf,ks='1']=process.argv; const H=fs.readFileSync(html,'utf8');
const Hum=new Function(H.match(/<script id="core">([\s\S]*?)<\/script>/)[1]+';return Hum;')();
const b=fs.readFileSync(wavf); let o=12,sr=0,ch=1,bits=16,data; while(o<b.length-8){ const id=b.toString('ascii',o,o+4),L=b.readUInt32LE(o+4); if(id==='fmt '){ch=b.readUInt16LE(o+10);sr=b.readUInt32LE(o+12);bits=b.readUInt16LE(o+22);} if(id==='data')data=b.subarray(o+8,o+8+L); o+=8+L+(L&1); }
const n=data.length/(bits/8)/ch, x=new Float32Array(n); for(let i=0;i<n;i++){ let s=0; for(let c=0;c<ch;c++) s+=bits===16?data.readInt16LE((i*ch+c)*2)/32768:data.readFloatLE((i*ch+c)*4); x[i]=s/ch; }
const r=sr/16000, N=Math.floor(n/r), y=new Float32Array(N); for(let i=0;i<N;i++){ let s=0,c=0; for(let k=Math.floor(i*r);k<Math.floor((i+1)*r);k++){ s+=x[k]; c++; } y[i]=s/c; }
let pk=0; for(const v of y) pk=Math.max(pk,Math.abs(v)); for(let i=0;i<N;i++) y[i]*=0.9/pk;
const tr0=Hum.track(y,16000); if(process.env.SWIFT){ const sp=require('path').join(process.env.SWIFT,require('path').basename(wavf).replace(/\.wav$/,'.json')); if(fs.existsSync(sp)) { const sw=JSON.parse(fs.readFileSync(sp,'utf8')); Hum.useSwift(tr0,sw,process.env.SWMODE==='vib'?Hum.swiftMask(tr0,sw):undefined); } }
const F=Hum.frames(tr0); const kS=+ks, opt={keyStrength:kS,keyMode:kS===0?'off':'on',switchCost:10};
// same steps as the page's redecode()
const tune=Hum.tuningCurve(F); let notes=Hum.decode(F,tune,null,opt), key=null;
if(notes.length>=3){ key=Hum.detectKey(notes); if(kS>0) notes=Hum.decode(F,tune,key,opt); key=Hum.detectKey(notes); }
if(notes.length>=4) Hum.refine(F,tune,notes);
if(process.env.NOSHAPE){ const raw=Hum.decode(F,tune,kS>0?key:null,opt); console.log("before shaping:",raw.map(o=>Hum.flatName(o.pitch)+"@"+o.start.toFixed(2)+"("+o.rel+")").join(" ")); }
notes=Hum.decode(F,tune,kS>0?key:null,{...opt,shape:1});
if(process.env.DRIFT&&key){ const k2=Hum.driftKey(notes)||key; Hum.applyDrift(F,tune,Hum.followDrift(Hum.decode(F,tune,k2,{...opt,shape:1}),k2)); key=Hum.recenter?Hum.recenter(tune,k2):k2; notes=Hum.decode(F,tune,key,{...opt,shape:1}); }
fs.writeFileSync(outf,JSON.stringify({t0:F.t0,dt:F.dt,mv:Array.from(F.mv||F.m),vib:Array.from(F.vib||[]),m:Array.from(F.m),voiced:Array.from(F.voiced),nv:F.nv?Array.from(F.nv,v=>Math.round(v*100)/100):[],ds:Array.from(F.ds,v=>Math.round(v*10)/10),curve:Array.from(tune.curve),key:key&&key.name,notes}));
console.log('key',key&&key.name,'| grid offset start',Math.round(100*tune.curve[0]),'end',Math.round(100*tune.curve[tune.curve.length-1]),'cents');
console.log(notes.map(o=>Hum.flatName(o.pitch)+'('+(o.rel>0?'+':'')+o.rel+')').join(' '));
