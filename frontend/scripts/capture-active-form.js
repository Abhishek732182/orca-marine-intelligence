import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const artifactsDir = 'C:\\Users\\PUSHTAM\\.gemini\\antigravity-ide\\brain\\dad6a0b5-d67f-41a6-9ced-cfaa998cf679';
const profileDir = path.join(artifactsDir, 'scratch', 'edge_test_profile2');

fs.mkdirSync(profileDir, { recursive: true });

const edgeProc = spawn(edgePath, [
  '--headless=new',
  '--remote-debugging-port=9226',
  '--disable-gpu',
  '--no-first-run',
  '--no-default-browser-check',
  `--user-data-dir=${profileDir}`,
  '--window-size=1280,1050',
  'about:blank',
]);

await new Promise((r) => setTimeout(r, 2000));

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

  async setInput(selector, value) {
    await this.eval(`
      (() => {
        const el = document.querySelector(${JSON.stringify(selector)});
        if (!el) return false;
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        setter.call(el, ${JSON.stringify(value)});
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
      })()
    `);
  }

  async captureScreenshot(outputPath) {
    const res = await this.send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(outputPath, Buffer.from(res.data, 'base64'));
    console.log(`Saved screenshot to: ${outputPath}`);
  }
}

try {
  const newTargetRes = await fetch('http://127.0.0.1:9226/json/new?http://localhost:5173/', { method: 'PUT' });
  const target = await newTargetRes.json();
  const client = new CDPClient(target.webSocketDebuggerUrl);
  await client.ready();
  await client.send('Page.enable');
  await client.send('Runtime.enable');

  await new Promise((r) => setTimeout(r, 1500));

  await client.setInput('#register-fullname', 'Dr. Rachel Carson');
  await client.setInput('#register-email', 'rachel.carson@orca-marine.org');
  await client.setInput('#register-password', 'Ocean#2026Secure');
  await client.setInput('#register-confirmpassword', 'Ocean#2026Secure');
  await new Promise((r) => setTimeout(r, 600));

  const screenshotPath = path.join(artifactsDir, 'orca_registration_form_active.png');
  await client.captureScreenshot(screenshotPath);
  process.exit(0);
} catch (err) {
  console.error(err);
  process.exit(1);
} finally {
  edgeProc.kill();
}
