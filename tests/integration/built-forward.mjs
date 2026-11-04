// Compiled-UI acceptance against a synthetic, signed FILE peer. No MT5 or orders.
import { spawn, execFileSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { mkdir, mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { resolve, join } from 'node:path';
import { chromium, expect } from '@playwright/test';

const root = process.cwd();
const directory = await mkdtemp(join(tmpdir(), 'aurum-built-'));
const python = resolve(root, process.platform === 'win32' ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python');
const token = randomBytes(48).toString('base64url');
const key = randomBytes(32).toString('hex');
const env = { ...process.env, AURUM_SESSION_TOKEN: token, AURUM_BRIDGE_KEY_HEX: key, AURUM_BACKEND_MODE: 'file', AURUM_ENV: 'development', AURUM_EA_ACCOUNT: 'demo-123', AURUM_BRIDGE_DIRECTORY: join(directory, 'common'), AURUM_DATABASE_PATH: join(directory, 'test.sqlite'), AURUM_ALLOWED_ORIGINS: 'http://127.0.0.1:1420', AURUM_LOCAL_DEV: '1' };
let output = '';
const children = [];
const start = args => {
    const child = spawn(python, args, { cwd: resolve(root, 'backend'), env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
    children.push(child); for (const stream of [child.stdout, child.stderr]) stream.on('data', chunk => { output += chunk; }); return child;
};
const ready = async url => {
    for (let i = 0; i < 100; i++) {
        try { if ((await fetch(url, { headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(500) })).ok) return; } catch { /* bounded readiness */ }
        await new Promise(r => setTimeout(r, 100));
    } throw Error('Built service startup failed');
};
const stop = async child => {
    if (child.exitCode !== null || child.signalCode !== null) return;
    const closed = new Promise(done => child.once('close', done));
    if (process.platform === 'win32') execFileSync('taskkill', ['/pid', String(child.pid), '/t', '/f'], { windowsHide: true, stdio: 'ignore' });
    else child.kill(); await closed;
};
let browser;
try {
    start(['-c', `import os,time
from pathlib import Path
from tests.test_bridge_file import message
from aurum_backend.bridge.files import AtomicFiles
from aurum_backend.bridge.codec import SignedCodec
files=AtomicFiles(Path(os.environ['AURUM_BRIDGE_DIRECTORY']))
codec=SignedCodec(bytes.fromhex(os.environ['AURUM_BRIDGE_KEY_HEX']))
instance=None
for seq in range(1,120):
 p=message(seq=seq,instance=instance); instance=p['ea_instance_id']
 p['body']['resources']['EaState']['account_currency']='USD'
 files.write('state.json',codec.encode(p)); time.sleep(1)
`]);
    let backend = start(['-m', 'aurum_backend.main']);
    start(['-m', 'tools.dashboard']);
    await ready('http://127.0.0.1:8765/api/v2/forward-test');
    await ready('http://127.0.0.1:1420');
    browser = await chromium.launch();
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:1420/overview');
    await expect(page.getByRole('button', { name: 'Download full JSON report' })).toBeEnabled({ timeout: 15000 });
    await expect(page.getByTestId('server-fixture-label')).toHaveCount(0);
    await expect(page.getByRole('link', { name: /Validation/ })).toHaveCount(0);
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download full JSON report' }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/^aurum-forward-.*\.json$/);
    const stream = await download.createReadStream(); let content = ''; for await (const chunk of stream) content += chunk;
    const report = JSON.parse(content);
    expect(report.samples).toBeGreaterThan(0); expect(report.decisions).toBeGreaterThan(0);
    expect(report.records.decisions.length).toBe(report.decisions);
    expect(content.includes(token) || content.includes(key)).toBe(false);
    await mkdir(resolve(root, 'backend/.evidence/forward-release'), { recursive: true });
    await page.screenshot({ path: resolve(root, 'backend/.evidence/forward-release/built-dashboard.png'), fullPage: true });
    await stop(backend);
    backend = start(['-m', 'aurum_backend.main']);
    await ready('http://127.0.0.1:8765/api/v2/forward-test');
    await page.reload();
    await expect(page.getByRole('button', { name: 'Download full JSON report' })).toBeEnabled({ timeout: 15000 });
    expect(errors).toEqual([]);
    console.log('PASS: compiled UI + secure session bootstrap + signed synthetic FILE peer + durable report + JSON download + backend restart');
} finally {
    await browser?.close();
    for (const child of children) await stop(child);
    await rm(directory, { recursive: true, force: true });
    if (output.includes(token) || output.includes(key)) { console.error('Credential appeared in service output'); process.exitCode = 1; }
}
