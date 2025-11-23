const https = require("https");
const fs = require("fs");

const WebSocket = require('ws');

const PORT = process.env.PORT || 8080;
const MODE = process.env.SERVER_MODE || 'insecure';
const VALID_TOKEN = process.env.VALID_TOKEN;

//const wss = new WebSocket.Server({ port: PORT });
const clients = new Map(); // clientId -> ws
// Create HTTPS server using your certificates
const server = https.createServer({
  key: fs.readFileSync("/certs/key.pem"),
  cert: fs.readFileSync("/certs/cert.pem"),
});

// Create WebSocket server attached to HTTPS
const wss = new WebSocket.Server({ server });

// Start HTTPS/WSS on port 8443
server.listen(8443, () => {
  console.log("Secure signaling server running on https://localhost:8443");
});

function send(ws, msg) {
  try { ws.send(JSON.stringify(msg)); } catch (e) { /* ignore */ }
}

wss.on('connection', (ws) => {
  console.log('[+] New WebSocket connection');

  ws.on('message', (raw) => {
    let msg;
    try { msg = JSON.parse(raw); } catch (e) {
      console.log('[-] Invalid JSON:', raw.toString());
      return;
    }

    console.log('[*] Received message:', msg);

    if (msg.type === 'register' && msg.clientId) {
      if (MODE === 'secure' && msg.token !== VALID_TOKEN) {
        console.log('[-] Invalid token for:', msg.clientId);
        send(ws, { type: 'error', reason: 'invalid token' });
        return ws.close();
      }
      ws.clientId = msg.clientId;
      clients.set(ws.clientId, ws);
      console.log('[+] Client registered:', msg.clientId, '- Total clients:', clients.size);
      send(ws, { type: 'registered', clientId: ws.clientId });
      return;
    }

    // routing messages with "to" field
    if (msg.to) {
      const target = clients.get(msg.to);
      console.log('[*] Routing message from', ws.clientId, 'to', msg.to, '- Target found:', !!target);
      console.log('[*] Available clients:', Array.from(clients.keys()));
      if (target && target.readyState === WebSocket.OPEN) {
        // attach from if available
        const out = Object.assign({}, msg, { from: msg.from || ws.clientId });
        send(target, out);
        console.log('[+] Message forwarded');
      } else {
        console.log('[-] Target unavailable:', msg.to);
        send(ws, { type: 'error', reason: 'target-unavailable', to: msg.to });
      }
    }
  });

  ws.on('close', () => {
    console.log('[-] Client disconnected:', ws.clientId);
    if (ws.clientId) clients.delete(ws.clientId);
  });
});

//console.log(Signaling server listening on ${PORT} (mode=${MODE}));