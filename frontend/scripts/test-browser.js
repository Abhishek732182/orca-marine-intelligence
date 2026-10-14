import { spawn } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs';

const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
const artifactsDir = process.env.ARTIFACTS_DIR || path.join(os.tmpdir(), 'orca-browser-artifacts');
const profileDir = path.join(artifactsDir, 'scratch', 'chrome_profile');

fs.mkdirSync(profileDir, { recursive: true });

console.log('Testing Chrome launch at:', chromePath);
console.log('Profile Dir:', profileDir);

const chromeProc = spawn(chromePath, [
  '--headless=new',
  '--remote-debugging-port=9222',
  '--disable-gpu',
  '--no-first-run',
  '--no-default-browser-check',
  `--user-data-dir=${profileDir}`,
  'about:blank',
]);

chromeProc.on('error', (err) => {
  console.error('Failed to spawn Chrome:', err);
  process.exit(1);
});

// Wait 2 seconds for CDP port to open
await new Promise((r) => setTimeout(r, 2000));

try {
  const res = await fetch('http://127.0.0.1:9222/json');
  const json = await res.json();
  console.log('Chrome CDP responded successfully. Target count:', json.length);
  console.log('First target:', json[0]?.title, json[0]?.url);
} catch (e) {
  console.error('Failed to connect to Chrome CDP:', e.message);
} finally {
  chromeProc.kill('SIGTERM');
  console.log('Chrome process closed.');
}
