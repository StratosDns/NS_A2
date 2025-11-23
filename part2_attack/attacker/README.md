# Registration Hijacking Attacker – Task 2 (PART 2.1)

This directory contains the **implementation and usage instructions** for the
**registration hijacking attack** against the signaling server used in the
WebRTC demo application.

The attacker:

- Connects to the **signaling server** (default: `ws://localhost:8080`)
- Sends a **registration message** using a **victim’s `clientId`** (e.g. `client-a`)
- Successfully **registers as the victim**
- **Logs all messages** it sends and receives over the WebSocket connection

The implementation is written in **Python**, but a `package.json` is also
included to declare the dependency if a Node.js implementation is added in the future.

---

## 1. Directory Contents

This README assumes the following files are in the **same folder**:

```text
attacker/
├── attacker.py         # Main Python attacker script (Task 2.1 implementation)
├── README.md           # This file
├── requirements.txt    # Python dependencies
├── package.json        # Node.js dependency declaration (optional / future use)
└── attacker.log        # Attacker logs (created automatically)
```

**Notes:**

- `attacker.py` is the main executable script.
- `requirements.txt` is used by `pip` to install the necessary Python packages.
- `package.json` is provided to satisfy the assignment requirement for a
  Node-style dependency file and to enable a future Node.js implementation,
  but the current attack code is in Python.

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
     to the console and to a log file (e.g. `attacker.log`).

---

## 3. Prerequisites

### 3.1. System Requirements

- **Python**: 3.8 or newer (3.9+ recommended)
- **pip**: Python package manager
- **Optional** (not required for the Python attacker):
  - Node.js (if a Node-based implementation is added later)

### 3.2. Python Dependencies

All Python dependencies are declared in `requirements.txt`.

Typical content (for reference):

```text
websockets>=12.0
```

The `attacker.py` script uses the `websockets` library to implement the
WebSocket connection, send/receive messages, and handle basic error conditions.

---

## 4. Installation and Setup

**Important:** All commands below assume the current working directory is the one
containing `attacker.py`, `requirements.txt`, and this `README.md`.

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

Once the virtual environment is activated (or in a global Python environment):

```bash
pip install -r requirements.txt
```

This installs `websockets` and any other required libraries.

---

## 5. Configuration and Command-Line Arguments

The attacker is controlled via **command-line arguments** when
invoking `attacker.py`.

### 5.1. Main Arguments

The script supports (at minimum) the following arguments:

- `--victim-id` (required)  
  - The **clientId to impersonate**.  
  - Example: `client-a`, `client-b`, or any other ID known to the application.

- `--server-url` (optional, default: `ws://localhost:8080`)  
  - The WebSocket URL of the **signaling server** or **proxy**.
  - Examples:
    - Direct connection to the signaling server:
      - `ws://localhost:8080`
    - Connection via a WebSocket proxy:
      - `ws://localhost:8081`

- `--log-file` (optional, default: `attacker.log`)  
  - Path to the file where **all activity will be logged**.

The exact argument names and defaults are defined inside `attacker.py` using
`argparse`. To see the arguments as implemented:

```bash
python attacker.py --help
```

---

## 6. Running the Attacker

### 6.1. Basic Example (Direct to Signaling Server)

Assuming:

- The signaling server is running at `ws://localhost:8080`
- The attacker should impersonate `client-a`

Run:

```bash
python attacker.py --victim-id client-a
```

This uses:

- `--server-url` default: `ws://localhost:8080`
- `--log-file` default: `attacker.log`

### 6.2. Using a Custom Server URL

If a WebSocket proxy is running on `ws://localhost:8081` and the attacker should
connect through it:

```bash
python attacker.py --server-url ws://localhost:8081 --victim-id client-a
```

The victim ID can be changed as needed:

```bash
python attacker.py --server-url ws://localhost:8081 --victim-id client-b
```

### 6.3. Custom Log File Location

To store logs in a different file or directory:

```bash
python attacker.py   --victim-id client-a   --server-url ws://localhost:8080   --log-file logs/attacker_client_a.log
```

If the directory part of the `--log-file` path does not exist, it must be
created manually or by additional logic.

---

## 7. Understanding the Output and Logs

The attacker produces **two types of output**:

1. **Console output** (standard output / standard error)  
2. **Log file output** (e.g. `attacker.log`)

### 7.1. Console Output

Typical console messages include:

- Connection lifecycle:
  - `[+] Connecting to ws://localhost:8080 as victim "client-a"...`
  - `[+] WebSocket connection established`
- Registration:
  - `[C → S] Registration message (impersonating 'client-a'): {...}`
  - `[S → C] Raw message: {"type":"registered","clientId":"client-a"}`
- Incoming messages:
  - `[S → C] Raw message: {"from":"client-b","to":"client-a","type":"offer", ...}`
- Errors:
  - `[!] Connection error: <error details>`
  - `[!] Failed to parse JSON message: ...`

Conventions:

- Messages prefixed with `[C → S]` are **sent** by the attacker.
- Messages prefixed with `[S → C]` are **received** from the server.
- Prefixes such as `[+]`, `[*]`, `[!]` represent status information or errors.

### 7.2. Log File

All of the above (and potentially more detailed timestamps) are also written to
the log file specified by `--log-file` (default: `attacker.log`).

A typical log snippet:

```text
2025-11-20T16:30:12Z [*] Starting registration hijacking attack: server='ws://localhost:8080', victim_id='client-a', display_name='attacker-client-a'
2025-11-20T16:30:12Z [*] Connecting to signaling server at 'ws://localhost:8080' ...
2025-11-20T16:30:12Z [+] Connected to signaling server.
2025-11-20T16:30:12Z [C → S] Registration message (impersonating 'client-a'): {"type": "register", "clientId": "client-a", "meta": {"displayName": "evil-attacker"}}
2025-11-20T16:30:12Z [S → C] Raw message: {"type":"registered","clientId":"client-a"}
2025-11-20T16:30:12Z [S → C] JSON message (pretty-printed):
{
  "clientId": "client-a",
  "type": "registered"
}
...
```

These logs provide evidence that the attacker successfully registers as the
victim and receives messages intended for that `clientId`.

---

## 8. Example Usage in an End-to-End Scenario

A typical end-to-end scenario using the attacker with the WebRTC demo is:

1. Start the **signaling server** (as provided by the assignment).
2. Start **Client A** (e.g. at `http://localhost:3001`) and click “Start / Offer”.
3. Start **Client B** (e.g. at `http://localhost:3002`) and click “Ready”.
4. Verify that Clients A and B can establish a WebRTC connection (audio/video).
5. Run the attacker, impersonating `client-a`:
   ```bash
   python attacker.py --victim-id client-a
   ```
6. Observe, in the `attacker.log` file and in the browser clients, that:
   - The server accepts the attacker as `client-a`.
   - Messages intended for Client A can now be observed or intercepted by the attacker.

---

## 9. Error Handling and Common Issues

The attacker script is designed to **handle errors gracefully** and report them
clearly. Common issues include:

### 9.1. Connection Refused

**Symptom:**

```text
[!] Connection error: [Errno 111] Connection refused
```

**Cause:**  
The signaling server (or proxy) is **not running** at the specified
`--server-url`.

**Resolution:**

- Start the signaling server or proxy.
- Confirm the correct WebSocket URL (host and port).
- Re-run the attacker:
  ```bash
  python attacker.py --victim-id client-a --server-url ws://localhost:8080
  ```

### 9.2. Invalid URL / Protocol (wss vs ws)

If `https://...` is used instead of `ws://` / `wss://`, or if `wss://` is used
without a properly configured TLS server, URL/SSL errors may occur.

**Resolution:**

- Ensure a valid WebSocket URL is used, e.g.:
  - `ws://localhost:8080`
  - `ws://localhost:8081`
- Use `wss://` only if the signaling server is configured for TLS.

### 9.3. JSON Parse Errors

If the server sends malformed JSON (unlikely in the provided demo) or if the
script is modified incorrectly, messages like the following may appear:

```text
[!] Failed to parse JSON message: ...
```

**Resolution:**

- Inspect the offending message in the logs.
- Ensure that all messages sent by the attacker are generated via `json.dumps()`.
- Avoid manual string construction with mismatched quotes or braces.

### 9.4. Multiple Registrations for the Same ID

Depending on the signaling server implementation, registering the same
`clientId` from multiple connections may:

- Disconnect the older client and keep the new registration, or  
- Reject the new registration, or  
- Allow both and result in undefined behavior.

The attacker does not assume a specific policy. It simply logs:

- The registration message it sends, and  
- The response from the server.

These logs are then used to analyze the server’s behavior.

---

## 10. `package.json` (Node.js Dependency Declaration)

Although the current implementation is in Python, the assignment also requires
a **dependencies file such as `package.json`**. The provided `package.json`:

- Declares the `ws` library as a dependency (for a potential future Node.js attacker).
- Serves as a template if a Node.js implementation (`attacker.js`) is created.

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

Running `npm install` is only necessary if a Node.js version of the attacker
is implemented.

---

## 11. Security and Ethical Considerations

This attacker is implemented **solely for educational and academic purposes**
within the context of a controlled Network Security exercise.

- It must **not** be run against any real-world system, service, or network
  without explicit, written permission.
- It is intended for use only with the provided local signaling server and test
  WebRTC clients.
- Misuse of these techniques can be **illegal** and is strictly prohibited.

By running this code, the user acknowledges these restrictions.

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
5. Inspect console output and `attacker.log` to confirm:
   - Successful connection
   - Successful registration as `client-a`
   - Logging of all messages

This README documents the implementation and usage of the registration
hijacking attacker for the signaling server.
