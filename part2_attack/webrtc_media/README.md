# WebRTC Media Interception Attacker – Task 2.3

This directory contains the implementation and usage instructions for the **media-interception attacker** used in Task **2.3 – Media Interception** of the Network Security assignment.

The attacker:

- Connects to the **WebSocket signaling server** (default: `ws://localhost:8080`).
- **Hijacks the registration** for a victim client ID (typically `client-b`), reusing the registration-hijacking idea from Task 2.1.
- **Intercepts the WebRTC offer** that **Client A** sends to the victim (`client-b`).
- Creates its own **`RTCPeerConnection`** using `aiortc`.
- Sends a valid **WebRTC answer** back to Client A via the signaling server.
- Exchanges ICE candidates and establishes a **direct media connection** between the attacker and Client A.
- **Records the received audio/video stream** to a local media file (by default, a `.webm` file).

The attacker does **not** display live video. Instead, it saves the intercepted media to disk so that it can be inspected later as evidence of a successful media-layer compromise.

---

## 1. Directory Structure

This README assumes the following files and directories are present in `webrtc_media/`:

```text
webrtc_media/
├── interceptor_webrtc.py         # Main Python script for Section 2.3 (media interception attacker)
├── README.md                     # This file
├── requirements.txt              # Python dependencies (aiortc, websockets, etc.)
└── recordings/                   # Output directory for intercepted media
    └── intercepted_media.webm    # Example output file (created at runtime)
```

Notes:

- `interceptor_webrtc.py` is the main script you execute for the **media interception** task.
- `requirements.txt` lists the Python packages required by the script.
- The `recordings/` directory is used to store the resulting media file. If it does not exist, the script will create it automatically before recording.

---

## 2. High-Level Overview of the Attack

At a high level, the media-interception attack works as follows:

1. **WebSocket connection and registration hijack**
   - The attacker connects to the signaling server via WebSocket (default `ws://localhost:8080`).
   - It sends a **registration message** using the victim’s `clientId` (in our experiments: `client-b`).
   - The signaling server accepts this registration and treats the attacker as the legitimate `client-b`.

2. **Intercepting the WebRTC offer**
   - When Client A tries to call `client-b`, it sends a signaling message of the form:
     ```json
     {
       "to": "client-b",
       "from": "client-a",
       "type": "offer",
       "sdp": "v=0..."
     }
     ```
   - Because the attacker is now registered as `client-b`, this **offer message is delivered to the attacker** instead of the real Client B.

3. **Creating an RTCPeerConnection and generating an answer**
   - The attacker parses the intercepted SDP offer and applies it as the **remote description** of a new `RTCPeerConnection` created with `aiortc` (using a simple STUN configuration).
   - It then generates an SDP **answer**, sets it as the **local description**, and sends an `answer` message back to Client A through the signaling server:
     ```json
     {
       "to": "client-a",
       "type": "answer",
       "sdp": "<attacker's SDP answer>"
     }
     ```

4. **ICE candidate exchange**
   - As ICE candidates are sent from Client A (messages of type `"ice"`), the attacker adds them to its `RTCPeerConnection`.
   - When the attacker’s `RTCPeerConnection` discovers its own ICE candidates, it sends them back to Client A via the signaling server using the same JSON structure.

5. **Media interception and recording**
   - Once the WebRTC connection is established, media tracks from Client A start flowing to the attacker.
   - Incoming tracks (both **audio** and **video**) are attached to an `aiortc.contrib.media.MediaRecorder` instance, which writes the received media into a `.webm` file in the `recordings/` directory (by default `recordings/intercepted_media.webm`).
   - After the connection ends or the script exits cleanly, the recorder is stopped and the output file is finalized.

This flow satisfies the requirements for **Task 2.3**: interception of the offer, creation of a peer connection, sending an answer, establishing media, and saving the result.

---

## 3. Prerequisites

### 3.1. System Requirements

- **Python**: 3.10 or newer is recommended.
- **pip**: Python package manager.
- **ffmpeg**: Required by `aiortc` to handle media encoding/decoding.
  - On Debian/Ubuntu:
    ```bash
    sudo apt-get update
    sudo apt-get install ffmpeg
    ```
  - On Windows, install ffmpeg and ensure it is on your `PATH`.

### 3.2. Python Dependencies

The file `requirements.txt` in this directory should contain entries similar to:

```text
websockets>=12.0
aiortc>=1.5.0
```

These provide:

- `websockets` for the asynchronous WebSocket connection to the signaling server.
- `aiortc` for the WebRTC peer connection, ICE handling, and media recording.

---

## 4. Installation and Setup

All commands below assume that your shell’s current working directory is `webrtc_media/` (the folder containing `interceptor_webrtc.py` and `requirements.txt`).

### 4.1. (Recommended) Create and Activate a Virtual Environment

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

With the virtual environment activated (or in your global environment):

```bash
pip install -r requirements.txt
```

This installs `websockets`, `aiortc`, and any transitive dependencies.

---

## 5. Command-Line Arguments

The behavior of `interceptor_webrtc.py` is controlled via command-line arguments.

From inside `webrtc_media/`, you can display the help message with:

```bash
python interceptor_webrtc.py --help
```

The script supports the following main options:

- `--server-url`  
  - WebSocket URL of the signaling server (or proxy).  
  - Default: `ws://localhost:8080`.

- `--victim-id`  
  - Client ID to impersonate (the ID that will receive the call).  
  - **Default in the script**: `client-a`.  
  - **In our experiments** for Part 2.3, we run with:
    ```bash
    --victim-id client-b
    ```
    because Client A is the caller and Client B is the callee in the demo.

- `--display-name`  
  - Optional human-readable display name included in the registration message.  
  - Default: an automatically generated name based on the victim ID.

- `--output`  
  - Path to the media output file.  
  - Default: `recordings/intercepted_media.webm`.  
  - If the extension is `.webm`, the script explicitly uses WebM; other extensions may work depending on codec support.

Example (matching the report / logs):

```bash
python interceptor_webrtc.py   --server-url ws://localhost:8080   --victim-id client-b   --output recordings/intercepted_media.webm
```

---

## 6. Typical Execution Scenario (Section 3.3)

The following sequence describes how the attacker is used in the context of the full WebRTC demo:

1. **Start the signaling server**  
   Launch the signaling server provided by the assignment so it listens on `ws://localhost:8080`.

2. **Start the WebRTC clients and verify normal operation**
   - Open **Client A** in a browser (e.g. `http://localhost:3001`) and click **“Start / Offer”** so it acts as the caller.
   - Open **Client B** in another browser (e.g. `http://localhost:3002`) and click **“Ready”**.
   - Confirm that the two browsers can establish a normal WebRTC audio/video connection.

3. **Stop the normal call** (optional)  
   Stop the initial call if needed, so you start from a clean state for the interception scenario.

4. **Run the media-interception attacker**
   - In a terminal, from `webrtc_media/`, run:
     ```bash
     python interceptor_webrtc.py --victim-id client-b
     ```
   - This connects to the signaling server and registers as `client-b` with a display name such as `webrtc-attacker-client-b`.

5. **Trigger a new call from Client A**
   - In the Client A tab (`http://localhost:3001`), initiate a call toward `client-b` again (e.g. by pressing the “Start / Offer” button).
   - The offer intended for the real Client B is now delivered to the attacker instead.

6. **Observe logs and media recording**
   - In the terminal where the attacker is running, you should see log lines indicating:
     - Successful hijacking of registration for `client-b`.
     - Interception of an `"offer"` message with SDP.
     - Creation of the `RTCPeerConnection`.
     - Creation and sending of an `"answer"` message.
     - ICE candidates being received (and local candidates being sent).
     - Audio and video tracks being received and attached to the `MediaRecorder`.
     - The `MediaRecorder` starting and, eventually, the tracks ending.
   - After some time, stop the attack script with `Ctrl+C` or by letting the call end.

7. **Inspect the recorded media file**
   - Check that a file was created under `recordings/` (by default `recordings/intercepted_media.webm`).
   - Play it with any media player (e.g. `vlc`, `mpv`) to verify that video and audio from the call were successfully intercepted and stored.


---

## 7. Troubleshooting and Notes

- **Connection refused**  
  If you see messages indicating that the WebSocket connection could not be established:
  - Confirm that the signaling server is running at the URL specified with `--server-url`.
  - Verify host and port (default `ws://localhost:8080`).

- **Missing ffmpeg or codec issues**  
  If the recorder fails with errors related to codecs or `ffmpeg`:
  - Make sure `ffmpeg` is installed and available in your shell.
  - Use the default `.webm` output (it is the most straightforward option in this lab environment).

- **No media recorded**  
  If the output file is empty or very short:
  - Verify that the browser actually sent media (camera/microphone permissions granted).
  - Ensure the call was established (offer/answer and ICE candidates exchanged).
  - Let the call run for a bit before stopping the attacker, so there is enough data.

- **ICE candidate warnings**  
  In some runs you may see warnings when adding remote ICE candidates. In our local LAN/loopback setup, the connection still completes and media is received successfully.

---

## 8. Security Perspective

This media-interception attacker highlights the impact of weak signaling security:

- Because registration is not authenticated, an attacker can impersonate `client-b` (or any other ID).
- Once controlling the signaling identity, the attacker can:
  - Receive the offer intended for the real client.
  - Complete the WebRTC handshake directly with the caller.
  - Capture the media stream at the endpoint, even though the media is encrypted on the wire (DTLS-SRTP).

In a real deployment, this would be a serious confidentiality breach. It emphasizes the need for:

- Strong authentication and authorization at the signaling layer.
- Protection of signaling channels (e.g. TLS, robust session management).
- Proper validation of client identities before routing offers and answers.

---

## 9. Quick Start Summary

1. From `webrtc_media/`, create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # or .\.venv\Scripts\Activate.ps1 on Windows
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Ensure the signaling server is running at `ws://localhost:8080` and that the WebRTC demo clients (Client A and Client B) work normally.
4. Start the attacker:
   ```bash
   python interceptor_webrtc.py --victim-id client-b
   ```
5. Initiate a call from Client A to `client-b` and let the script run.
6. After the test, inspect `recordings/intercepted_media.webm` to confirm successful media interception.
