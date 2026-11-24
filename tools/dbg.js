// Loads the detection core from index.html into Node. Env switches for comparisons:
//   OLD=1      the rules as they were before today's changes
//   NOSHAPE=1  skip the final note-shape step
//   TRACE=a,b  print note pieces between a and b seconds at each shape step
const fs=require('fs'),path=require('path'),vm=require('vm');
const html=fs.readFileSync(path.join(__dirname,'..','index.html'),'utf8');
let C=html.match(/<script id="core">([\s\S]*?)<\/script>/)[1];
const sb={module:{exports:{}},Math,Float64Array,Float32Array,Uint8Array,Int16Array,Array,Number,isNaN,Object,JSON,Map,Set,console};
if(process.env.NOSHAPE||process.env.OLD) C=C.replace("kept=shape(kept);","0;");
if(process.env.OLD) C=C.replace("m=F.mv||F.m","m=F.m").replace("&&settle<5","");
if(process.env.TRACE){
  const [a,b]=process.env.TRACE.split(',').map(Number);
  sb.TR=(tag,l,dt)=>console.log(tag,l.filter(o=>o.b*dt>=a&&o.a*dt<=b).map(o=>o.pitch+'@'+(o.a*dt).toFixed(2)+'-'+(o.b*dt).toFixed(2)+(o.bs!=null?'('+o.bs.toFixed(2)+')':'')).join(' '));
  C=C.replace('    function shape(list){','    function shape(list){ TR("in",list,F.dt);')
     .replace('      // b) re-join','      TR("after-a",list,F.dt);\n      // b) re-join');
}
vm.createContext(sb); vm.runInContext(C,sb); module.exports=sb.module.exports;
