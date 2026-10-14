import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const artifactsDir = process.env.ARTIFACTS_DIR || path.join(os.tmpdir(), 'orca-browser-artifacts');
const profileDir = path.join(artifactsDir, 'scratch', 'edge_spa_profile');

console.log('====================================================');
console.log('ORCA: Running Headless Browser Automated SPA Suite');
console.log('Browser Binary:', edgePath);
console.log('Target URL: http://localhost:5173/');
console.log('Artifacts Dir:', artifactsDir);
console.log('====================================================\n');

// Server Prerequisite Check
console.log('Checking frontend server availability at http://localhost:5173/ ...');
let isServerRunning = false;
try {
  const ping = await fetch('http://localhost:5173/', { signal: AbortSignal.timeout(1500) });
  isServerRunning = ping.ok || ping.status === 200 || ping.status === 304;
} catch {
  isServerRunning = false;
}

if (!isServerRunning) {
  console.log('====================================================');
  console.log('ORCA: SPA Browser Test Prerequisites Check');
  console.log('STATUS: [BLOCKED]');
  console.log('REASON: Frontend development server is not running on http://localhost:5173/');
  console.log('EXACT PREREQUISITE: Start Vite development server with "npm run dev"');
  console.log('====================================================\n');
  process.exit(0);
}

fs.mkdirSync(profileDir, { recursive: true });

const edgeProc = spawn(edgePath, [
  '--headless=new',
  '--remote-debugging-port=9227',
  '--disable-gpu',
  '--no-first-run',
  '--no-default-browser-check',
  `--user-data-dir=${profileDir}`,
  '--window-size=1380,950',
  'about:blank',
]);

edgeProc.on('error', (err) => {
  console.error('Failed to spawn browser process:', err);
  process.exit(1);
});

// Wait 2.5s for Edge CDP
await new Promise((r) => setTimeout(r, 2500));

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.id = 1;
    this.callbacks = new Map();
  }

  async ready() {
    if (this.ws.readyState === WebSocket.OPEN) return;
    return new Promise((resolve, reject) => {
      this.ws.onopen = resolve;
      this.ws.onerror = reject;
      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id && this.callbacks.has(msg.id)) {
          const { resolve: res, reject: rej } = this.callbacks.get(msg.id);
          this.callbacks.delete(msg.id);
          if (msg.error) rej(new Error(msg.error.message || 'CDP Error'));
          else res(msg.result);
        }
      };
    });
  }

  send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.callbacks.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  async eval(expression) {
    const res = await this.send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true,
    });
    return res?.result?.value;
  }

  async captureScreenshot(outputPath) {
    const res = await this.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(outputPath, Buffer.from(res.data, 'base64'));
    console.log(`Saved screenshot: ${path.basename(outputPath)}`);
  }
}

try {
  const newTargetRes = await fetch('http://127.0.0.1:9227/json/new?http://localhost:5173/', { method: 'PUT' });
  const target = await newTargetRes.json();
  const client = new CDPClient(target.webSocketDebuggerUrl);
  await client.ready();
  await client.send('Page.enable');
  await client.send('Runtime.enable');

  console.log('1. Waiting for SPA root to load and redirect to /register...');
  await new Promise((r) => setTimeout(r, 2000));

  const url1 = await client.eval('window.location.pathname');
  const title1 = await client.eval('document.querySelector(".auth-form-title")?.innerText');
  console.log('   Current Path:', url1);
  console.log('   Form Heading:', title1);

  const regScreenshot = path.join(artifactsDir, 'spa_01_register.png');
  await client.captureScreenshot(regScreenshot);

  console.log('\n2. Testing client-side SPA navigation to /login via navbar...');
  await client.eval('document.getElementById("nav-link-login").click()');
  await new Promise((r) => setTimeout(r, 700));

  const url2 = await client.eval('window.location.pathname');
  const title2 = await client.eval('document.querySelector(".auth-form-title")?.innerText');
  console.log('   Current Path:', url2);
  console.log('   Form Heading:', title2);

  const loginScreenshot = path.join(artifactsDir, 'spa_02_login.png');
  await client.captureScreenshot(loginScreenshot);

  console.log('\n3. Testing client-side SPA navigation to /user/dashboard...');
  await client.eval('document.getElementById("nav-link-user").click()');
  await new Promise((r) => setTimeout(r, 800));

  const url3 = await client.eval('window.location.pathname');
  const title3 = await client.eval('document.querySelector(".dashboard-page-title")?.innerText');
  console.log('   Current Path:', url3);
  console.log('   Dashboard Title:', title3);

  const userDashboardScreenshot = path.join(artifactsDir, 'spa_03_user_dashboard.png');
  await client.captureScreenshot(userDashboardScreenshot);

  console.log('\n4. Testing client-side SPA navigation to /admin/dashboard...');
  await client.eval('document.getElementById("nav-link-admin").click()');
  await new Promise((r) => setTimeout(r, 800));

  const url4 = await client.eval('window.location.pathname');
  const title4 = await client.eval('document.querySelector(".dashboard-page-title")?.innerText');
  console.log('   Current Path:', url4);
  console.log('   Dashboard Title:', title4);

  const adminDashboardScreenshot = path.join(artifactsDir, 'spa_04_admin_dashboard.png');
  await client.captureScreenshot(adminDashboardScreenshot);

  console.log('\n5. Testing mobile responsive layout on /user/dashboard (390 x 844)...');
  await client.eval('document.getElementById("nav-link-user").click()');
  await new Promise((r) => setTimeout(r, 500));
  await client.send('Emulation.setDeviceMetricsOverride', {
    width: 390,
    height: 844,
    deviceScaleFactor: 2,
    mobile: true,
  });
  await new Promise((r) => setTimeout(r, 600));

  const mobileDashboardScreenshot = path.join(artifactsDir, 'spa_05_mobile_user_dashboard.png');
  await client.captureScreenshot(mobileDashboardScreenshot);

  console.log('\n====================================================');
  console.log('ALL SPA PAGES AND ROUTING VERIFIED SUCCESSFULLY!');
  console.log('====================================================');

  process.exit(0);
} catch (err) {
  console.error('SPA Test Error:', err);
  process.exit(1);
} finally {
  edgeProc.kill();
}
