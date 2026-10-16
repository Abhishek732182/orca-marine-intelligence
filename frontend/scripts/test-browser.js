import { spawn } from 'node:child_process';

const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';

console.log('Testing Chrome launch at:', chromePath);

const chromeProc = spawn(chromePath, [
  '--headless=new',
  '--remote-debugging-port=9222',
  '--disable-gpu',
  '--no-first-run',
  '--no-default-browser-check',
  '--user-data-dir=C:\\Users\\ABHINANDAN KUMAR\\.gemini\\antigravity-ide\\brain\\fe2a00e7-62f2-4ff1-80a0-9f788857f360\\scratch\\chrome_profile',
  'about:blank',
]);

chromeProc.on('error', (err) => {
  console.error('Failed to spawn Chrome:', err);
  process.exit(1);
});

// Wait 2 seconds for CDP port to open
await new Promise(r => setTimeout(r, 2000));

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
