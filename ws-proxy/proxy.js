// proxy.js
const fs = require('fs');
const logStream = fs.createWriteStream('proxy_2_2.log', { flags: 'a' });

function logline(...args) {
  const line = args.join(' ');
  console.log(line);
  logStream.write(line + '\n');
}


const WebSocket = require('ws');

const PROXY_PORT = 8081;
const TARGET_URL = 'ws://localhost:8080'; // real signaling server

const wss = new WebSocket.Server({ port: PROXY_PORT }, () => {
  logline(`[*] WebSocket proxy listening on ws://localhost:${PROXY_PORT}`);
  logline(`[*] Forwarding to ${TARGET_URL}`);
});

function logJson(tag, data) {
  const text = typeof data === 'string' ? data : data.toString();
  logline(`${tag} Raw:`, text);
  try {
    const json = JSON.parse(text);
    logline(`${tag} JSON:`, JSON.stringify(json, null, 2));
  } catch (e) {
    // not JSON, ignore
  }
}

wss.on('connection', (clientSocket, req) => {
  logline('\n[+] New client connected from', req.socket.remoteAddress);

  const serverSocket = new WebSocket(TARGET_URL);

  serverSocket.on('open', () => {
    logline('[*] Connected to real signaling server');
  });

  serverSocket.on('error', (err) => {
    console.error('[!] Error connecting to signaling server:', err.message);
    if (clientSocket.readyState === WebSocket.OPEN) {
      clientSocket.close();
    }
  });

  // Client → Server
  clientSocket.on('message', (data, isBinary) => {
    logJson('[C → S]', data);
    if (serverSocket.readyState === WebSocket.OPEN) {
      serverSocket.send(data, { binary: isBinary });
    }
  });

  // Server → Client
  serverSocket.on('message', (data, isBinary) => {
    logJson('[S → C]', data);
    if (clientSocket.readyState === WebSocket.OPEN) {
      clientSocket.send(data, { binary: isBinary });
    }
  });

  clientSocket.on('close', () => {
    logline('[*] Client connection closed');
    if (serverSocket.readyState === WebSocket.OPEN) {
      serverSocket.close();
    }
  });

  serverSocket.on('close', () => {
    logline('[*] Server connection closed');
    if (clientSocket.readyState === WebSocket.OPEN) {
      clientSocket.close();
    }
  });
});

wss.on('error', (err) => {
  console.error('[!] Proxy server error:', err.message);
});
