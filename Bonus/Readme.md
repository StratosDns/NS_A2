# NS Assignment 2 – Bonus Task: Enabling Secure WebRTC Signaling (WSS)

This repository contains the full implementation of the **Assignment 2 Bonus Task**, where the insecure WebSocket signaling channel (`ws://`) is upgraded to a secure WebSocket channel (`wss://`) using TLS certificates and Docker.

## Generate TLS Certificates
Inside the signaling server directory:

```bash
cd docker/signaling
nano ssl

openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout key.pem -out cert.pem -days 365 \
  -subj "/CN=localhost"
```
This generates:
- key.pem
- cert.pem

These will be mounted inside the signaling server container.

## Edit docker-compose to mount certs and open port 8443
Modify it so that it includes:
- The HTTPS/WSS port 8443
- A volume that mounts certs inside the container at /certs
```bash
ports:
      - "8080:8080"    # existing HTTP port
      - "8443:8443"    # NEW: HTTPS/WSS port
volumes:
      - ./docker/ssl:/certs:ro
```
## Modify the signaling server (server.js) to use HTTPS + WSS
Add required modules at the very top
```bash
const https = require("https");
const fs = require("fs");
```
Remove the old WebSocket server creation (or comment out)
```bash
const wss = new WebSocket.Server({ port: PORT });
```
Insert the HTTPS + WSS replacement
```bash
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
```
Remove old log line
```bash
console.log(`Signaling server listening on ${PORT} (mode=${MODE})`);
```
## Update the client to use wss://localhost:8443
in
```bash
docker/client/webrtc-static-server.js
```
replace
```bash
const wsHost = process.env.SIGNALING_URL.replace('signaling', 'localhost');
```
with
```bash
const wsHost = "wss://localhost:8443";
```
This forces the client to always use your new secure WebSocket endpoint.

## Rebuild Docker
```bash
docker compose down
docker compose build
docker compose up
```
Now when we try to run it we notice a pop up error notifying us
```bash
Failed to register. Please wait for WebSocket connection.
```
With a self-signed TLS cert, the reason is:
The browser doesn’t trust cert.pem, so the wss:// handshake fails.
We fix that by opening a new tab to
```bash
https://localhost:8443
```
A security warnging comes up and we simply accept the risk and continue and we are all set.
