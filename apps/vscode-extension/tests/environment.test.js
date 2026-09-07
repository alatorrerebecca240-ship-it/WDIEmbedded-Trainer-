const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const Module = require('node:module');
const {RuntimeEnvironment,defaults,launchEnvironment,sha256,verifyPayload,requiredComponents,resolveExecutable,manifest} = require('../src/environment');
const fakeEnv = {LOCALAPPDATA:'C:\\Users\\Student\\AppData\\Local',SystemRoot:'C:\\Windows',PROCESSOR_ARCHITECTURE:'AMD64',Path:''};
const good = {python:'C:\\working\\python.exe',c:'C:\\working\\gcc.exe',cpp:'C:\\working\\g++.exe',boost:'C:\\working\\boost'};
function fixture(options={}) {
  const writes=[], calls=[], lines=[];
  const context={extensionUri:{fsPath:path.resolve(__dirname,'..')},globalState:{get:()=>({...good}),update:async(k,v)=>writes.push([k,v])}};
  const runtime=new RuntimeEnvironment(context,{appendLine:s=>lines.push(s)},{platform:'win32',arch:'x64',env:fakeEnv,
    execute:async(...args)=>{calls.push(args);return {code:0,stdout:'',stderr:''}},verifyPayload:async()=>{},...options});
  return {runtime,writes,calls,lines};
}
test('default targets are current-user directories; unknown LocalAppData rejected',()=>{
  assert.match(defaults(fakeEnv).python,/Programs[\\/]Python[\\/]Python313$/);
  assert.match(defaults(fakeEnv).compiler,/Programs[\\/]EmbeddedTrainer[\\/]llvm-mingw/);
  assert.throws(()=>defaults({LOCALAPPDATA:'relative'}));
});
test('child environment is isolated and compiler bin added once without current directory',()=>{
  const input={Path:'C:\\Windows',CPLUS_INCLUDE_PATH:'C:\\old'};
  const env=launchEnvironment(good,input);
  assert.equal(input.Path,'C:\\Windows'); assert.equal(input.TRAINER_CC,undefined);
  assert.equal(env.TRAINER_CC,good.c); assert.equal(env.Path.split(path.delimiter).length,2);
  assert.ok(env.CPLUS_INCLUDE_PATH.startsWith(good.boost));
  assert.equal(launchEnvironment({c:'gcc'},{Path:'original'}).Path,'original');
});
test('component selection preserves working tools and keeps Boost optional to detection',()=>{
  assert.deepEqual(requiredComponents(good),[]);
  assert.deepEqual(requiredComponents({...good,cpp:undefined}),['compiler']);
  assert.deepEqual(requiredComponents({}),['python','compiler','boost']);
});
test('payload verification rejects missing, changed, and unknown files before execution',async(t)=>{
  const dir=await fs.mkdtemp(path.join(os.tmpdir(),'trainer-payload-test-'));
  t.after(()=>fs.rm(dir,{recursive:true,force:true}));
  await assert.rejects(verifyPayload(dir,'python'));
  await fs.writeFile(path.join(dir,manifest.python.file),'not an installer');
  assert.equal((await sha256(path.join(dir,manifest.python.file))).length,64);
  await assert.rejects(verifyPayload(dir,'python'),/校验失败/);
  await assert.rejects(verifyPayload(dir,'..'),/不支持/);
});
test('executable lookup uses absolute PATH entries and ignores workspace-relative entries',async(t)=>{
  const dir=await fs.mkdtemp(path.join(os.tmpdir(),'trainer-path-test-'));
  t.after(()=>fs.rm(dir,{recursive:true,force:true}));
  await fs.writeFile(path.join(dir,'gcc.exe'),'fixture');
  assert.equal(resolveExecutable('gcc',{Path:'.'+path.delimiter+dir},'win32'),path.join(dir,'gcc.exe'));
  assert.equal(resolveExecutable('gcc',{Path:'.'},'win32'),undefined);
});
test('every missing payload must pass verification before installer can start',async()=>{
  const seen=[];
  const {runtime,calls,writes}=fixture({verifyPayload:async(_,name)=>{seen.push(name);if(name==='compiler')throw Error('bad hash')}});
  await assert.rejects(runtime.install('C:\\bundle',{}),/bad hash/);
  assert.deepEqual(seen,['python','compiler']); assert.equal(calls.length,0); assert.equal(writes.length,0);
  assert.deepEqual(runtime.launch(),good);
});
test('installer failure does not persist paths or replace previous working settings',async()=>{
  const {runtime,writes}=fixture({execute:async()=>({code:1,stdout:'failed',stderr:''})});
  await assert.rejects(runtime.install('C:\\bundle',{}),/未完成/);
  assert.deepEqual(runtime.launch(),good); assert.equal(writes.length,0);
});
test('installation preserves each working compiler and holds new paths until recheck',async()=>{
  const {runtime,calls,writes}=fixture();
  const result=await runtime.install('C:\\bundle with spaces',{...good,cpp:undefined});
  assert.equal(result.c,good.c); assert.equal(result.python,good.python);
  assert.match(result.cpp,/clang\+\+\.exe$/); assert.equal(writes.length,0);
  assert.ok(calls[0][1].includes('C:\\bundle with spaces'));
  assert.equal(calls[0][1].at(-1),'compiler');
  assert.equal(calls[0][2].env.Path,'');
  assert.equal(calls[0][2].env.PSModulePath,path.join(path.dirname(calls[0][0]),'Modules'));
});
test('nothing missing means no installer or validation execution',async()=>{
  const {runtime,calls}=fixture({verifyPayload:async()=>assert.fail('unexpected verification')});
  await runtime.install('ignored',good); assert.equal(calls.length,0);
});
test('unsupported OS or emulated ARM64 cannot install x64 bundle',async()=>{
  for(const options of [{platform:'linux'},{arch:'arm64'},{env:{...fakeEnv,PROCESSOR_ARCHITEW6432:'ARM64'}}]){
    const {runtime,calls}=fixture(options);await assert.rejects(runtime.install('ignored',{}),/Windows/);assert.equal(calls.length,0);
  }
});
test('detection reuses working Python and checks both languages with own smoke code',async(t)=>{
  const dir=await fs.mkdtemp(path.join(os.tmpdir(),'trainer-detect-test-'));t.after(()=>fs.rm(dir,{recursive:true,force:true}));
  const selected={python:path.join(dir,'python.exe'),c:path.join(dir,'gcc.exe'),cpp:path.join(dir,'g++.exe')};
  for(const p of Object.values(selected))await fs.writeFile(p,'fixture');
  const calls=[];const {runtime,writes}=fixture({env:{...fakeEnv,Path:dir},execute:async(file,args)=>{
    calls.push([file,args]);return {code:0,stdout:file===selected.python?JSON.stringify({path:file,ok:true}):'gcc Free Software Foundation',stderr:''};
  }});
  runtime.runtime=selected;
  const report=await runtime.detect(selected.python,dir);
  assert.equal(report.python,selected.python);assert.equal(report.c,selected.c);assert.equal(report.cpp,selected.cpp);
  assert.equal(writes.at(-1)[1].pythonSetting,selected.python);
  assert.ok(calls.some(([,a])=>a.includes('-std=c11')));assert.ok(calls.some(([,a])=>a.includes('-std=c++17')));
});

let responses=[],events=[];
const vscode={ProgressLocation:{Notification:1},workspace:{getConfiguration:()=>({get:()=> 'custom-python'})},window:{
  showInformationMessage:async(...a)=>events.push(['info',...a]),
  showWarningMessage:async(...a)=>{events.push(['warning',...a]);return responses.shift()},
  showErrorMessage:async(...a)=>events.push(['error',...a]),
  showOpenDialog:async()=>responses.shift(),withProgress:async(_,fn)=>fn({report:()=>{}})
}};
const original=Module._load;let checkEnvironment;
let TrainerBackend;
try{Module._load=function(name,...args){return name==='vscode'?vscode:original.call(this,name,...args)};
  ({checkEnvironment}=require('../src/environment-ui'));
  ({TrainerBackend}=require('../src/backend'));}finally{Module._load=original}
async function ui(report,answers,install=async()=>{}){
  responses=[...answers];events=[];let installs=0,doctors=0,refreshes=0;
  const runtime={busy:false,detect:async()=>report,install:async(...a)=>{installs++;await install(...a)}};
  const backend={rootUri:{fsPath:'C:\\practice'},output:{appendLine:()=>{},show:()=>{}},run:async()=>{doctors++;return {code:0}}};
  await checkEnvironment(runtime,backend,async()=>{refreshes++});
  assert.equal(runtime.busy,false);return {installs,doctors,refreshes,events:[...events]};
}
test('UI working environment never asks to install',async()=>{const r=await ui(good,[]);assert.equal(r.installs,0);assert.equal(r.doctors,1);assert.equal(r.refreshes,1)});
test('UI declining optional Boost still refreshes recovered course list',async()=>{const r=await ui({...good,boost:undefined},['暂不安装']);assert.equal(r.installs,0);assert.equal(r.doctors,1);assert.equal(r.refreshes,1)});
test('UI missing environment cancel before choosing directory executes nothing',async()=>{const r=await ui({},['暂不安装']);assert.equal(r.installs,0);assert.equal(r.doctors,0)});
test('UI final explicit confirmation required before installing',async()=>{const r=await ui({},['从离线包自动安装',[{fsPath:os.tmpdir()}],undefined]);assert.equal(r.installs,0)});
test('UI install errors are surfaced and busy guard released',async()=>{const r=await ui({},['从离线包自动安装',[{fsPath:os.tmpdir()}],'确认并按默认路径安装'],async()=>{throw Error('hash mismatch')});assert.equal(r.installs,1);assert.equal(r.doctors,0);assert.ok(r.events.some(x=>x[0]==='error'&&x[1]==='hash mismatch'))});
test('successful UI installation rechecks tools before doctor and refreshing courses',async()=>{
  responses=['从离线包自动安装',[{fsPath:os.tmpdir()}],'确认并按默认路径安装'];events=[];
  const order=[],settings=[];
  const runtime={busy:false,detect:async setting=>{settings.push(setting);order.push('detect');return settings.length===1?{}:good},install:async()=>order.push('install')};
  const backend={rootUri:{fsPath:'C:\\practice'},output:{appendLine:()=>{},show:()=>{}},run:async()=>{order.push('doctor');return {code:0}}};
  await checkEnvironment(runtime,backend,async()=>order.push('refresh'));
  assert.deepEqual(order,['detect','install','detect','doctor','refresh']);
  assert.deepEqual(settings,['custom-python','custom-python']);assert.equal(runtime.busy,false);
});
test('backend uses verified local Python only while it matches current configuration',()=>{
  const runtime={launch:()=>({...good,pythonSetting:'custom-python'})};
  const backend=new TrainerBackend({fsPath:'C:\\practice'},{},{},{runtime});
  assert.equal(backend.pythonPath,good.python);
  runtime.launch=()=>({...good,pythonSetting:'previous-setting'});
  assert.equal(backend.pythonPath,'custom-python');
});
