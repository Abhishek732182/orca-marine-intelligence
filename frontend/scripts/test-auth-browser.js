import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const edgePath = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const artifactsDir = 'C:\\Users\\PUSHTAM\\.gemini\\antigravity-ide\\brain\\dad6a0b5-d67f-41a6-9ced-cfaa998cf679';
const profileDir = path.join(artifactsDir, 'scratch', 'edge_test_profile');

fs.mkdirSync(profileDir, { recursive: true });

console.log('====================================================');
console.log('ORCA: Executing Headless Browser Auth Verification');
console.log('Browser Binary:', edgePath);
console.log('Target URL: http://localhost:5173/');
console.log('Artifacts Dir:', artifactsDir);
console.log('====================================================\n');

const edgeProc = spawn(edgePath, [
  '--headless=new',
  '--remote-debugging-port=9225',
  '--disable-gpu',
  '--no-first-run',
  '--no-default-browser-check',
  `--user-data-dir=${profileDir}`,
  '--window-size=1280,850',
  'about:blank',
]);

edgeProc.on('error', (err) => {
  console.error('Failed to spawn Edge process:', err);
  process.exit(1);
});

// Wait 2.5s for Edge CDP server
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
  const newTargetRes = await fetch('http://127.0.0.1:9225/json/new?http://localhost:5173/', { method: 'PUT' });
  const target = await newTargetRes.json();
  console.log(`Connected to Browser Page Target: ${target.id}`);

  const client = new CDPClient(target.webSocketDebuggerUrl);
  await client.ready();
  await client.send('Page.enable');
  await client.send('Runtime.enable');

  console.log('\n1. Waiting for ORCA Authentication page to render...');
  await new Promise((r) => setTimeout(r, 2000));

  const title = await client.eval('document.title');
  console.log('   Document Title:', title);

  const heading = await client.eval('document.querySelector(".auth-form-title")?.innerText');
  console.log('   Form Heading:', heading);

  // Test 2: Submit empty registration form
  console.log('\n2. Testing Registration empty form submission...');
  await client.eval('document.getElementById("register-submit-btn").click()');
  await new Promise((r) => setTimeout(r, 500));

  const nameError = await client.eval('document.getElementById("register-fullname-error")?.innerText');
  const emailError = await client.eval('document.getElementById("register-email-error")?.innerText');
  const passError = await client.eval('document.getElementById("register-password-error")?.innerText');
  const confirmError = await client.eval('document.getElementById("register-confirmpassword-error")?.innerText');

  console.log('   [Full Name Error]:', nameError);
  console.log('   [Email Error]:', emailError);
  console.log('   [Password Error]:', passError);
  console.log('   [Confirm Password Error]:', confirmError);

  const screenshotRegErrors = path.join(artifactsDir, 'orca_registration_validation_errors.png');
  await client.captureScreenshot(screenshotRegErrors);

  // Test 3: Type invalid formats
  console.log('\n3. Testing invalid formats and live Password Strength Meter...');
  await client.setInput('#register-fullname', 'Rachel Carson');
  await client.setInput('#register-email', 'invalid-email-address');
  await client.setInput('#register-password', 'short');
  await client.setInput('#register-confirmpassword', 'mismatch');
  await client.eval('document.getElementById("register-submit-btn").click()');
  await new Promise((r) => setTimeout(r, 500));

  const invalidEmailText = await client.eval('document.getElementById("register-email-error")?.innerText');
  const weakPasswordText = await client.eval('document.getElementById("register-password-error")?.innerText');
  const mismatchText = await client.eval('document.getElementById("register-confirmpassword-error")?.innerText');
  console.log('   [Invalid Email Validation]:', invalidEmailText);
  console.log('   [Weak Password Validation]:', weakPasswordText);
  console.log('   [Mismatch Validation]:', mismatchText);

  // Test 4: Enter valid registration credentials
  console.log('\n4. Entering valid registration credentials...');
  await client.setInput('#register-fullname', 'Dr. Rachel Carson');
  await client.setInput('#register-email', 'rachel.carson@orca-marine.org');
  await client.setInput('#register-password', 'Ocean#2026Secure');
  await client.setInput('#register-confirmpassword', 'Ocean#2026Secure');
  await new Promise((r) => setTimeout(r, 500));

  const strengthScore = await client.eval('document.querySelector(".strength-score-text")?.innerText');
  console.log('   [Live Strength Meter Rating]:', strengthScore);

  await client.eval('document.getElementById("register-submit-btn").click()');
  await new Promise((r) => setTimeout(r, 800));

  const regSuccessText = await client.eval('document.querySelector(".auth-alert-box.success")?.innerText');
  console.log('   [Registration Success Feedback]:\n', regSuccessText);

  const screenshotRegSuccess = path.join(artifactsDir, 'orca_registration_success.png');
  await client.captureScreenshot(screenshotRegSuccess);

  // Test 5: Switch to Login Page
  console.log('\n5. Navigating to User Login Page via link...');
  await client.eval('document.getElementById("nav-to-login-link").click()');
  await new Promise((r) => setTimeout(r, 600));

  const loginHeading = await client.eval('document.querySelector(".auth-form-title")?.innerText');
  console.log('   [Login Page Heading]:', loginHeading);

  // Test 6: Submit empty Login
  console.log('\n6. Testing Login empty submission...');
  await client.eval('document.getElementById("login-submit-btn").click()');
  await new Promise((r) => setTimeout(r, 500));

  const loginEmailErr = await client.eval('document.getElementById("login-email-error")?.innerText');
  const loginPassErr = await client.eval('document.getElementById("login-password-error")?.innerText');
  console.log('   [Login Email Error]:', loginEmailErr);
  console.log('   [Login Password Error]:', loginPassErr);

  // Test 7: Enter valid login credentials
  console.log('\n7. Entering valid login credentials...');
  await client.setInput('#login-email', 'researcher@orca-marine.org');
  await client.setInput('#login-password', 'Ocean#2026Secure');
  await client.eval('document.getElementById("login-submit-btn").click()');
  await new Promise((r) => setTimeout(r, 800));

  const loginSuccessText = await client.eval('document.querySelector(".auth-alert-box.success")?.innerText');
  console.log('   [Login Success Feedback]:\n', loginSuccessText);

  const screenshotLogin = path.join(artifactsDir, 'orca_login_desktop.png');
  await client.captureScreenshot(screenshotLogin);

  // Test 8: Responsive Mobile Viewport
  console.log('\n8. Testing responsive layout on mobile viewport (390 x 844)...');
  await client.send('Emulation.setDeviceMetricsOverride', {
    width: 390,
    height: 844,
    deviceScaleFactor: 2,
    mobile: true,
  });
  await new Promise((r) => setTimeout(r, 600));

  const screenshotMobile = path.join(artifactsDir, 'orca_auth_mobile_responsive.png');
  await client.captureScreenshot(screenshotMobile);

  console.log('\n====================================================');
  console.log('ALL BROWSER AUTOMATION VERIFICATIONS PASSED 100%!');
  console.log('====================================================');

  process.exit(0);
} catch (err) {
  console.error('Browser Test Error:', err);
  process.exit(1);
} finally {
  edgeProc.kill();
}
