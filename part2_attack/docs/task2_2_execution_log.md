# Task 2.2 – Registration Hijacking Execution Log

## Environment Setup

- Signaling server:
  - Command: navigating to the downloaded `Assignment 2` directory, inside the `docker` folder and running `docker compose build`and`docker compose up`
  - URL: `ws://localhost:8080`
- Client A URL: `http://localhost:3001`
- Client B URL: `http://localhost:3002`
- Attacker:
  - Script: `part2_attack/attacker/attacker.py`
  - Python version: 3.10
  - Dependencies: `websockets`, (see requirements.txt)

## Baseline – Normal WebRTC Session

1. Started signaling server.
2. Opened Client A and clicked “Start / Offer”.
3. Opened Client B and clicked “Ready”.
4. Observed successful audio/video connection.
5. Screenshots: `NS_A2/part2_attacker/screenshots`

## Attack Execution – Registration Hijacking

1. With both clients still running, started the attacker:

   ```bash
   cd NS_A2/part2_attack/attacker
   python attacker.py --server-url ws://localhost:8080 --victim-id client-a
   ```

2. Attacker sent a registration message using clientId = "client-a" and received:

    ```json
    {"type": "registered", "clientId": "client-a"}
    ```

3. Triggered renegotiation by clicking “Ready” again on Client B.

4. The attacker received messages with "to": "client-a" and "from": "client-b"

5. Screenshots:

    - `t2_2_step2_attacker_started.png`

    - `t2_2_step3_hijack_messages.png`

## Observed Impact on Legitimate Client A

- After the attacker registered:

    - Client A stopped receiving new signaling messages.

    - video frozen

    - Screenshot: `t2_2_step4_clientA_after_hijack.png`.