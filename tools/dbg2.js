const Hum=require('./dbg.js'); const fs=require('fs');
// reuse run.js loader
const src=fs.readFileSync(__dirname+'/run.js','utf8').split('const [,,file')[0].replace(/const Hum=.*\n/,'');
eval(src);
const {x,sr}=readWav(process.argv[2]); const y=resample(x,sr,16000); let pk=0; for(const v of y) pk=Math.max(pk,Math.abs(v)); for(let i=0;i<y.length;i++) y[i]*=0.9/pk;
const F=Hum.frames(Hum.track(y,16000)); const tune=Hum.tuningCurve(F); const opt={keyStrength:1,switchCost:10};
console.log('tune0 initial',Math.round(100*tune.curve[0]));
let n=Hum.decode(F,tune,null,opt); let key=Hum.detectKey(n); console.log('pass1 key',key.name,key.conf.toFixed(2));
n=Hum.decode(F,tune,key,opt); key=Hum.detectKey(n); console.log('pass2 key',key.name,key.conf.toFixed(2));
Hum.refine(F,tune,n); console.log('after refine tune0',Math.round(100*tune.curve[0]),'tune@13.5',Math.round(100*tune.curve[Math.round((13.5-F.t0)/F.dt)]));
n=Hum.decode(F,tune,key,opt); key=Hum.detectKey(n); console.log('pass3 key',key.name,key.conf.toFixed(2));
