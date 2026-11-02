import { spawn, execFileSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { createServer } from 'node:net';
import { resolve, join, dirname, basename } from 'node:path';
import { mkdir, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { once } from 'node:events';
import { chromium, expect } from '@playwright/test';

const root=process.cwd();
const freePort=()=>new Promise((done,reject)=>{const server=createServer();server.once('error',reject);server.listen(0,'127.0.0.1',()=>{const port=server.address().port;server.close(()=>done(port));});});
const port=await freePort();
const origin=`http://127.0.0.1:${port}`;
const token=randomBytes(48).toString('base64url');
const environment={...process.env,AURUM_SESSION_TOKEN:token,AURUM_ENV:'development',AURUM_SCENARIO:'normal',AURUM_BACKEND_MODE:'fixture',AURUM_ALLOWED_ORIGINS:origin,VITE_USE_MOCKS:'false'};
const children=[];
let output='';
const capture=child=>{children.push(child);for(const stream of [child.stdout,child.stderr])stream.on('data',chunk=>{output+=chunk.toString();});return child;};
const startBackend=extra=>capture(spawn(resolve(root,process.platform==='win32'?'backend/.venv/Scripts/aurum-backend.exe':'backend/.venv/bin/aurum-backend'),[],{cwd:resolve(root,'backend'),env:{...environment,...extra},windowsHide:true,stdio:['ignore','pipe','pipe']}));
let backend=startBackend({});
const vite=spawn(process.execPath,[resolve(root,'node_modules/vite/bin/vite.js'),'--host','127.0.0.1','--port',String(port),'--strictPort'],{cwd:root,env:environment,windowsHide:true,stdio:['ignore','pipe','pipe']});
capture(vite);
const directory=await mkdtemp(join(tmpdir(),'aurum-integration-'));
const bridgeKey=randomBytes(32).toString('hex');
let browser;
async function stop(child){
 if(child.exitCode!==null||child.signalCode!==null)return;
 const exited=once(child,'close');
 if(process.platform==='win32'&&child.pid){try{execFileSync('taskkill',['/pid',String(child.pid),'/t','/f'],{stdio:'ignore',windowsHide:true});}catch{/* process may already have exited */}}
 else child.kill();
 await exited;
}
async function ready(url,headers={}){for(let i=0;i<100;i++){try{const response=await fetch(url,{headers,signal:AbortSignal.timeout(500)});if(response.ok)return;}catch{/* bounded startup polling */}await new Promise(r=>setTimeout(r,100));}throw Error('Integration server startup timed out');}
try{
 await ready('http://127.0.0.1:8765/api/v1/status',{Authorization:`Bearer ${token}`});
 await ready(origin);
 browser=await chromium.launch();
 const page=await browser.newPage({viewport:{width:1440,height:900}});
 const frames=[];
 const socketUrls=[];
 page.on('websocket',socket=>{if(new URL(socket.url()).port!=='8765')return;socketUrls.push(socket.url());socket.on('framesent',frame=>frames.push(String(frame.payload)));});
 await page.goto(origin+'/overview');
 // Emulates only the existing limited native command's in-memory session handoff.
 await page.evaluate(async value=>{const client=await import('/src/shared/api/client.ts');client.setSessionToken(value);},token);
 await expect(page.getByRole('button',{name:'Halt entries'})).toBeEnabled({timeout:15000});
 await expect(page.getByTestId('server-fixture-label')).toBeVisible();
 expect(frames.some(frame=>JSON.parse(frame).type==='authenticate')).toBe(true);
 expect(socketUrls.every(url=>new URL(url).search==='')).toBe(true);
 expect(frames.every(frame=>!frame.includes(token))).toBe(true);
 await page.getByRole('link',{name:/Configuration/}).click();
 await page.locator('input[name="maxSpread"]').fill('30');
 await page.getByRole('button',{name:'Validate and review changes'}).click();
 await page.getByRole('button',{name:'Apply and await acknowledgement'}).click();
 await expect(page.getByText(/EA acknowledged/)).toBeVisible();
 await expect(page.getByText('EA configuration · v8',{exact:true})).toBeVisible();
 // A second edit must use the acknowledged version and a new idempotency key.
 await page.locator('input[name="maxSpread"]').fill('25');
 await page.getByRole('button',{name:'Validate and review changes'}).click();
 await page.getByRole('button',{name:'Apply and await acknowledgement'}).click();
 await expect(page.getByText('EA configuration · v9',{exact:true})).toBeVisible();
 await mkdir('docs/screenshots/integration',{recursive:true});
 await page.screenshot({path:'docs/screenshots/integration/python-dashboard.png',fullPage:true});
 console.log('PASS: real FastAPI + browser + one-use WS ticket + fixture label + two successive settings Acks');
 await page.close();
 await stop(backend);
 backend=startBackend({AURUM_BACKEND_MODE:'file',AURUM_BRIDGE_DIRECTORY:join(directory,'common'),AURUM_DATABASE_PATH:join(directory,'state.sqlite'),AURUM_BRIDGE_KEY_HEX:bridgeKey,AURUM_EA_ACCOUNT:'integration-no-ea'});
 await ready('http://127.0.0.1:8765/api/v1/status',{Authorization:`Bearer ${token}`});
 const missing=await fetch('http://127.0.0.1:8765/api/v1/ea/state',{headers:{Authorization:`Bearer ${token}`}});
 expect(missing.status).toBe(503);
 const filePage=await browser.newPage({viewport:{width:1440,height:900}});
 await filePage.goto(origin+'/overview');
 await filePage.evaluate(async value=>{const client=await import('/src/shared/api/client.ts');client.setSessionToken(value);},token);
 await expect(filePage.locator('.health-node').filter({hasText:'EA'})).toContainText('offline',{timeout:15000});
 await expect(filePage.getByRole('button',{name:'Halt entries'})).toBeDisabled();
 await expect(filePage.getByTestId('server-fixture-label')).toHaveCount(0);
 await filePage.screenshot({path:'docs/screenshots/integration/file-no-ea.png',fullPage:true});
 console.log('PASS: real FILE backend + browser + missing EA remains offline/unavailable + commands disabled');
}finally{
 await browser?.close();
 for(const child of children) await stop(child);
 const target=resolve(directory);
 if(dirname(target)!==resolve(tmpdir())||!basename(target).startsWith('aurum-integration-')){console.error('FAIL: unexpected cleanup target');process.exitCode=1;}
 else await rm(target,{recursive:true,force:true});
 if(output.includes(token)||output.includes(bridgeKey)){console.error('FAIL: credential leaked to child-process output');process.exitCode=1;}
}
