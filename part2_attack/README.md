# Registration Hijacking Attacker – Task 2.1 (PART 2)

This directory contains the **implementation and usage instructions** for the
**registration hijacking attack** against the signaling server used in the
WebRTC demo application.

The attacker:

- Connects to the **signaling server** (default: `ws://localhost:8080`)
- Sends a **registration message** using a **victim’s `clientId`** (e.g. `client-a`)
- Successfully **registers as the victim**
- **Logs all messages** it sends and receives over the WebSocket connection

The implementation is written in **Python**, but a `package.json` is also
included to declare the dependency if you later port the attacker to Node.js.


---

## 1. Directory Contents

This README assumes the following files are in the **same folder**:

```text
attacker/
├── attacker.py         # Main Python attacker script (Task 2.1 implementation)
├── README.md           # This file
├── requirements.txt    # Python dependencies
├── package.json        # Node.js dependency declaration (optional / future use)
└── logs/               # Directory for attacker logs (created automatically)
    └── attacker.log    # Example run log (generated at runtime)
```

**Notes:**

- `attacker.py` is the main executable script you will run.
- `requirements.txt` is used by `pip` to install the necessary Python packages.
- `package.json` is provided to satisfy the assignment requirement for a
  Node-style dependency file and to enable a future Node.js implementation,
  but the current attack code is in Python.
- The `logs/` directory is created automatically the first time the script runs
  (if it does not already exist).


---

## 2. High-Level Attack Overview

At a high level, the attack performs the following steps:

1. **Connects** to the signaling server via WebSocket  
   - Default URL: `ws://localhost:8080`  
   - Configurable via command-line argument (e.g. to use a proxy at `ws://localhost:8081`)

2. **Sends a registration message** with a **spoofed `clientId`**  
   - For example, the attacker pretends to be `client-a`:
     ```json
     {
       "type": "register",
       "clientId": "client-a",
       "meta": {
         "displayName": "evil-attacker"
       }
     }
     ```

3. **Waits for the server’s response**  
   - Typically a message like:
     ```json
     {
       "type": "registered",
       "clientId": "client-a"
     }
     ```
   - If received, it indicates that the server has accepted the attacker as the
     registered owner of that `clientId`.

4. **Stays connected and logs all messages**  
   - Any messages from the server that are **addressed to the victim’s ID**
     will now be delivered to the attacker’s WebSocket connection.
   - The attacker script **logs every message** (incoming and outgoing), both
     to the console and to a log file (e.g. `logs/attacker.log`).

This matches the requirements of **Task 2.1: Craft the Attack**.


---

## 3. Prerequisites

### 3.1. System Requirements

- **Python**: 3.8 or newer (3.9+ recommended)
- **pip**: Python package manager
- **Optional** (not required for Python attacker):
  - Node.js (if you want to experiment with a Node-based implementation later)

### 3.2. Python Dependencies

All Python dependencies are declared in `requirements.txt`.

Typical content (for reference):

```text
websocket-client>=1.8.0
```

The `attacker.py` script uses the `websocket-client` library to implement the
WebSocket connection, send/receive messages, and handle basic error conditions.


---

## 4. Installation and Setup

**Important:** All commands below assume you are in the directory that contains
`attacker.py`, `requirements.txt`, and this `README.md`.

### 4.1. (Optional but Recommended) Create a Virtual Environment

On Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 4.2. Install Python Dependencies

Once the virtual environment is activated (or in your global Python environment):

```bash
pip install -r requirements.txt
```

This installs `websocket-client` and any other required libraries.

### 4.3. Check the Installation

You can quickly verify that Python sees the dependencies by running:

```bash
python -c "import websocket; print('websocket-client OK')"
```

If no error appears, you are ready to run the attacker.


---

## 5. Configuration and Command-Line Arguments

The attacker is controlled primarily via **command-line arguments** when
invoking `attacker.py`.

### 5.1. Main Arguments

The script supports (at minimum) the following arguments:

- `--victim-id` (required)  
  - The **clientId you want to impersonate**.  
  - Example: `client-a`, `client-b`, or any other ID known to the application.

- `--server-url` (optional, default: `ws://localhost:8080`)  
  - The WebSocket URL of the **signaling server** or **proxy**.
  - Examples:
    - Direct connection to the real signaling server:
      - `ws://localhost:8080`
    - Connection via your WebSocket proxy:
      - `ws://localhost:8081`

- `--log-file` (optional, default: `logs/attacker.log`)  
  - Path to the file where **all activity will be logged**.
  - If the `logs/` directory does not exist, the script creates it.

Your exact argument names and defaults are defined inside `attacker.py` using
`argparse`. The README assumes:

```text
--victim-id   = ID to impersonate
--server-url  = ws://<host>:<port> of signaling server
--log-file    = path to log file
```

You can always run:

```bash
python attacker.py --help
```

to see the exact names and descriptions of the available options, as reported
by the script itself.


---

## 6. Running the Attacker

### 6.1. Basic Example (Direct to Signaling Server)

Assuming:

- Signaling server is running at `ws://localhost:8080`
- You want to impersonate `client-a`

Run:

```bash
python attacker.py --victim-id client-a
```

This uses:

- `--server-url` default: `ws://localhost:8080`
- `--log-file` default: `logs/attacker.log`

### 6.2. Using a Custom Server URL

If, for example, you are running a WebSocket proxy on `ws://localhost:8081`
and want the attacker to connect through that:

```bash
python attacker.py --server-url ws://localhost:8081 --victim-id client-a
```

You can change the victim ID as needed:

```bash
python attacker.py --server-url ws://localhost:8081 --victim-id client-b
```

### 6.3. Custom Log File Location

To store logs in a different file or directory:

```bash
python attacker.py   --victim-id client-a   --server-url ws://localhost:8080   --log-file logs/attacker_client_a.log
```

If the directory part of the `--log-file` path does not exist, make sure to
create it in advance or rely on the script’s automatic directory creation
(if implemented).

---

## 7. Understanding the Output and Logs

The attacker produces **two types of output**:

1. **Console output** (standard output / standard error)
2. **Log file output** (e.g. `logs/attacker.log`)

### 7.1. Console Output

Typical console messages might include:

- Connection lifecycle:
  - `[+] Connecting to ws://localhost:8080 as victim "client-a"...`
  - `[+] WebSocket connection established`
- Registration:
  - `[>] Sent registration message: {"type": "register", ...}`
  - `[<] Received server response: {"type": "registered", "clientId": "client-a"}`
- Incoming messages:
  - `[<] From server: {"from":"client-b", "to":"client-a", "type":"offer", ...}`
- Errors:
  - `[!] Connection error: <error details>`
  - `[!] JSON parse error for message: ...`

The exact format depends on how logging is implemented in `attacker.py`, but in
all cases:

- Messages **starting with `[>]`** represent data **sent** by the attacker.
- Messages **starting with `[<]`** represent data **received** from the server.
- Messages **starting with `[!]`** represent **warnings** or **errors**.

### 7.2. Log File

All of the above (and possibly more detailed timestamps) are also written to
the log file specified by `--log-file` (default: `logs/attacker.log`).

A sample log snippet may look like:

```text
2025-11-20 16:30:12 [INFO] Connecting to ws://localhost:8080 as victim "client-a"
2025-11-20 16:30:12 [INFO] WebSocket connection established
2025-11-20 16:30:12 [SEND] {"type": "register", "clientId": "client-a", "meta": {"displayName": "evil-attacker"}}
2025-11-20 16:30:12 [RECV] {"type":"registered","clientId":"client-a"}
2025-11-20 16:30:20 [RECV] {"from":"client-b","to":"client-a","type":"offer", ...}
...
```

These logs will be very useful for **Task 2.2**, where you must provide
captured messages and step-by-step attack documentation.


---

## 8. Typical Usage in the Full Scenario

While Task 2.1 only requires the attack script itself, in practice you may use
it in the following broader scenario (used later in Task 2.2):

1. Start the **signaling server** (as provided by the assignment).
2. Start **Client A** (e.g. at `http://localhost:3001`) and click “Start / Offer”.
3. Start **Client B** (e.g. at `http://localhost:3002`) and click “Ready”.
4. Verify that they can establish a WebRTC connection (audio/video).
5. Run the **attacker**, impersonating `client-a`:
   ```bash
   python attacker.py --victim-id client-a
   ```
6. Observe in:
   - The **logs** that the server accepts the attacker as `client-a`.
   - The **browser clients** that messages intended for Client A may now be
     misrouted or the legitimate A behaves unexpectedly (depending on server behavior).

Task 2.2 will require you to capture screenshots and document this behavior in
detail; this README focuses on the **code and usage** for Task 2.1.


---

## 9. Error Handling and Common Issues

The attacker script is designed to **handle errors gracefully** and report them
clearly. Here are some common issues:

### 9.1. Connection Refused

**Symptom:**

```text
[!] Connection error: [Errno 111] Connection refused
```

**Cause:**  
The signaling server (or proxy) is **not running** at the specified
`--server-url`.

**Fix:**

- Start the signaling server / proxy.
- Confirm the correct WebSocket URL (host and port).
- Re-run:
  ```bash
  python attacker.py --victim-id client-a --server-url ws://localhost:8080
  ```

### 9.2. Invalid URL / Protocol (wss vs ws)

If you mistakenly provide `https://...` instead of `ws://` / `wss://`, or if
you try to use `wss` without proper SSL support, you might see URL or SSL
errors.

**Fix:**

- Ensure you are using the **WebSocket URL**, e.g.:
  - `ws://localhost:8080`
  - `ws://localhost:8081`
- Only use `wss://` if the signaling server is actually configured for TLS.

### 9.3. JSON Parse Errors

If the server sends malformed JSON (unlikely in a controlled assignment) or if
you modify the script and break JSON handling, you might see errors like:

```text
[!] Failed to parse JSON message: ...
```

**Fix:**

- Check the exact message printed in the logs.
- Verify that **all messages you send** are valid JSON via `json.dumps()`.
- Avoid manually crafting strings with mismatched quotes or braces.

### 9.4. Multiple Registrations for the Same ID

Depending on how the signaling server is implemented, registering the same
`clientId` from multiple connections may:

- Disconnect the older client and keep the **new registration**, or  
- Reject the new registration attempt, or  
- Allow both and behave unpredictably.

The attacker is written in a generic way and **does not rely on a specific
policy**. Instead, it logs:

- What it **sent** as registration
- What the **server responded**

You will analyze this behavior in detail when you document the attack results.


---

## 10. `package.json` (Node.js Dependency Declaration)

Although the current implementation is in Python, the assignment also asks for
a **dependencies file such as `package.json`**. The provided `package.json`:

- Declares the `ws` library as a dependency (for a future Node.js attacker).
- Serves as a template if you decide to re-implement the attacker in Node.js.

Example content (for reference):

```json
{
  "name": "registration-hijack-attacker",
  "version": "1.0.0",
  "description": "WebSocket signaling server registration hijacking attack (Task 2.1)",
  "main": "attacker.js",
  "dependencies": {
    "ws": "^8.0.0"
  }
}
```

You **do not** need to run `npm install` unless you decide to implement
`attacker.js` as a Node.js alternative. For Task 2.1, the **Python version**
(`attacker.py`) is sufficient.


---

## 11. Security and Ethical Disclaimer

This attacker is implemented **solely for educational and academic purposes**
within the context of the Network Security assignment.

- **Do not** run this code against any real-world system, service, or network
  that you do not own or have explicit, written permission to test.
- Use it **only** with the provided local signaling server and test WebRTC
  clients.
- Misuse of these techniques can be **illegal** and is strictly prohibited.

By running this code, you acknowledge that you understand and accept these
restrictions.


---

## 12. Quick Start Summary

1. Ensure the signaling server (and optional proxy) are running.
2. In this directory, create and activate a virtual environment (optional):
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # or .\.venv\Scripts\Activate.ps1 on Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the attacker (impersonating `client-a`):
   ```bash
   python attacker.py --victim-id client-a
   ```
5. Inspect console output and `logs/attacker.log` to confirm:
   - Successful connection
   - Successful registration as `client-a`
   - Logging of all messages

This completes the **Task 2.1** usage requirements for the registration
hijacking attacker.
