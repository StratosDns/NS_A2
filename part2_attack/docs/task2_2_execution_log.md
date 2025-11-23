# Task 2.2 – Registration Hijacking Attack Execution Log

This document describes, step-by-step, how the registration hijacking attack
was executed and observed in practice, following the test scenario described in
Task 2.2.

The goal of the experiment is to demonstrate that, after the attacker registers
as `client-a`, signaling messages that should be delivered to the legitimate
Client A are instead delivered to the attacker process.

---

## 1. Environment Setup

### 1.1 Signaling Server

- The signaling server provided with the assignment was started using Docker.
- Commands (from the assignment’s server directory):
  ```bash
  docker compose build
  docker compose up
  ```
- After startup, the server exposes a WebSocket signaling endpoint at:
  ```text
  ws://localhost:8080
  ```

### 1.2 WebRTC Clients

Two browser-based WebRTC clients were used:

- **Client A (caller)**  
  - URL: `http://localhost:3001`  
  - Role in the scenario: initiates the call and sends the initial WebRTC offer.

- **Client B (callee)**  
  - URL: `http://localhost:3002`  
  - Role in the scenario: receives the offer and returns an answer.

Both clients were opened in a desktop browser on the same machine as the
signaling server.

### 1.3 Attacker

- Attack implementation:  
  - Script: `NS_A2/part2_attack/attacker/attacker.py`
  - Language: Python 3 (virtual environment created in the same directory)
- Dependencies:
  - Installed from `NS_A2/part2_attack/attacker/requirements.txt`:
    ```text
    websockets>=12.0
    ```
- Example virtual environment setup:
  ```bash
  cd NS_A2/part2_attack/attacker
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
- Default WebSocket endpoint used by the attacker:
  ```text
  ws://localhost:8080
  ```
- Default log file:
  ```text
  attacker.log
  ```

---

## 2. Baseline: Normal WebRTC Session (No Attacker)

This section confirms that the two WebRTC clients can communicate normally
without the attacker present.

1. **Start the signaling server**

   The signaling server is started as described in Section 1.1 using:
   ```bash
   docker compose build
   docker compose up
   ```

2. **Open Client A (caller)**

   - Navigate to `http://localhost:3001`.
   - Click the **“Start / Offer”** button.
   - Client A creates a WebRTC offer and sends the corresponding signaling
     messages (offer + ICE candidates) to the signaling server.

3. **Open Client B (callee)**

   - In a separate browser window or tab, navigate to `http://localhost:3002`.
   - Click the **“Ready”** button.
   - Client B receives the offer from Client A via the signaling server,
     creates an answer, and sends it back.

4. **Verify audio/video connectivity**

   - Both peers now display remote audio/video streams.
   - The screenshot `t2_2_step1_clients_connected.png` (stored under  
     `NS_A2/part2_attack/screenshots/`) documents this baseline state,
     showing that the two clients are connected and media flows correctly.

At this point, the system behaves as intended: the signaling server correctly
routes messages between Client A and Client B using their respective
`clientId`s.

---

## 3. Attack Execution: Hijacking Client A’s Registration

This section follows the test scenario steps while introducing the attacker.

### 3.1 Prepare a Stable Call Before the Attack

1. **Repeat the baseline call setup**

   - Ensure the signaling server is running at `ws://localhost:8080`.
   - Open:
     - Client A at `http://localhost:3001` and click “Start / Offer”.
     - Client B at `http://localhost:3002` and click “Ready”.
   - Confirm that the two clients again establish a bidirectional audio/video
     connection.

2. **Capture the pre-attack media state**

   - The screenshot `t2_2_step2_attack_caller_start_media.png` shows the normal
     media session before the attacker connects.
   - `t2_2_step2_attack_caller_stop_media.png` captures the state immediately
     before or after the attack, still from the caller’s perspective, to
     document the transition.

### 3.2 Launch the Registration Hijacking Attacker

3. **Start the attacker script (impersonating Client A)**

   In a new terminal:

   ```bash
   cd NS_A2/part2_attack/attacker
   source .venv/bin/activate        # if not already active
   python attacker.py --server-url ws://localhost:8080 --victim-id client-a
   ```

   - The attacker connects directly to the signaling server at
     `ws://localhost:8080`.
   - It immediately sends a `register` message using `clientId = "client-a"`.

4. **Confirm successful registration as the victim**

   In the attacker’s console and `attacker.log` we observe:

   ```text
   2025-11-20T23:01:38Z [*] Starting registration hijacking attack: server='ws://localhost:8080', victim_id='client-a', display_name='attacker-client-a'
   2025-11-20T23:01:38Z [*] Connecting to signaling server at 'ws://localhost:8080' ...
   2025-11-20T23:01:38Z [+] Connected to signaling server.
   2025-11-20T23:01:38Z [C → S] Registration message (impersonating 'client-a'): {"type": "register", "clientId": "client-a", "meta": {"displayName": "attacker-client-a"}}
   2025-11-20T23:01:38Z [S → C] Raw message: {"type":"registered","clientId":"client-a"}
   2025-11-20T23:01:38Z [S → C] JSON message (pretty-printed):
   {
     "clientId": "client-a",
     "type": "registered"
   }
   ```

   - This shows that the signaling server has accepted the attacker’s
     registration for `clientId = "client-a"`.
   - The screenshot `t2_2_step2_attacker_started.png` documents this step,
     showing the attacker terminal with the registration log output.

### 3.3 Trigger New Signaling Messages and Observe Hijacking

5. **Trigger additional signaling from Client B**

   - With the attacker still running and registered as `client-a`, return to
     Client B (`http://localhost:3002`).
   - Interact with the UI to trigger new signaling messages (for example,
     by clicking “Ready” again or restarting the offer/answer exchange).
   - Any new offers/answers/ICE candidates targeting `client-a` are now routed
     to the attacker’s WebSocket connection rather than to the legitimate
     Client A.

6. **Observe hijacked messages in the attacker log**

   In `attacker.log`, additional messages from the server to the attacker
   appear, for example:

   ```text
   2025-11-20T23:02:10Z [S → C] Raw message: {"to":"client-a","from":"client-b","type":"offer", ...}
   2025-11-20T23:02:11Z [S → C] Raw message: {"to":"client-a","from":"client-b","type":"ice","candidate":{...}}
   ```

   - These messages demonstrate that the attacker is now receiving offers and
     ICE candidates originally intended for `client-a`.
   - The screenshot `t2_2_step3_hijack_messages.png` shows the attacker’s
     terminal with such hijacked messages highlighted.

---

## 4. Observed Impact on Legitimate Client A

After the attacker registers successfully as `client-a`:

- The signaling server associates the `client-a` identifier with the attacker
  connection.
- Subsequent signaling messages addressed to `client-a` (such as renegotiation
  offers and ICE candidates) are delivered to the attacker instead of the
  legitimate Client A.
- On the legitimate Client A browser tab:
  - The remote video stream eventually **freezes** and stops updating when
    new signaling is triggered.
  - Client A no longer receives fresh signaling messages required to
    renegotiate or maintain the call.
  - The UI may still show the call as “connected”, but the media session is
    effectively broken from Client A’s perspective.

These effects are documented visually in the screenshot
`t2_2_step4_clientA_after_hijack.png`, stored under:

```text
NS_A2/part2_attack/screenshots/t2_2_step4_clientA_after_hijack.png
```

This completes the step-by-step execution log required for Task 2.2.
