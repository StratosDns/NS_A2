# Task 2.2 – Description of Impact on Legitimate Client A

This document explains how the registration hijacking attack affects the
legitimate Client A once the attacker has successfully registered as
`client-a`.

---

## 1. Change in Signaling Ownership

During normal operation, the signaling server maintains a mapping from each
`clientId` (e.g. `"client-a"`, `"client-b"`) to the corresponding WebSocket
connection. When the attacker connects and sends:

```json
{
  "type": "register",
  "clientId": "client-a",
  "meta": {
    "displayName": "attacker-client-a"
  }
}
```

the server responds with:

```json
{
  "type": "registered",
  "clientId": "client-a"
}
```

From this point on, the server associates the identifier `"client-a"` with the
attacker’s WebSocket connection. The legitimate Client A may still have an
open WebSocket connection, but it is no longer the active owner of the
`client-a` identity in the signaling layer.

---

## 2. Effect on Signaling Messages

After the attacker has taken over the `client-a` identity:

- **New offers from Client B:**
  - When Client B triggers another offer (e.g. by clicking “Ready” again or
    restarting the call flow), the signaling server forwards that offer to
    the connection registered as `client-a`.
  - Because the attacker is now registered under `client-a`, the **offer is
    delivered to the attacker** instead of to the legitimate Client A.

- **New ICE candidates from Client B:**
  - Similarly, any ICE candidates that should be sent from Client B to
    `client-a` are also delivered to the attacker.
  - The attacker’s log shows messages of the form:
    ```json
    {
      "to": "client-a",
      "from": "client-b",
      "type": "ice",
      "candidate": { ... }
    }
    ```
  - The legitimate Client A no longer receives these candidates.

As a result, the legitimate Client A stops receiving the signaling information
needed to maintain or renegotiate the WebRTC session.

---

## 3. User-Visible Impact on Client A

From the perspective of the user sitting at Client A:

- The remote video stream from Client B **freezes** and stops updating once
  new signaling (offer/ICE) is triggered after the hijack.
- Client A does not obtain fresh SDP or ICE information, so:
  - It cannot correctly renegotiate the media session.
  - It cannot recover the media connection on its own.
- The browser UI may still show the call interface and controls, which can
  mislead the user into thinking the call is still active, even though the
  media path is effectively broken.

This behaviour is documented in the screenshot:

```text
NS_A2/part2_attack/screenshots/t2_2_step4_clientA_after_hijack.png
```

where the remote video from Client B is visibly stuck and no longer
responsive.

---

## 4. Security Implications

The observed impact highlights two important security issues:

1. **Loss of availability for the legitimate client**

   - Even without decrypting or manipulating the media, the attacker can
     **disrupt** Client A’s ability to communicate by silently hijacking its
     signaling identity.
   - This enables denial-of-service and session disruption attacks targeted at
     specific users.

2. **Potential for more advanced man-in-the-middle attacks**

   - Since the attacker now receives offers and ICE candidates intended for
     `client-a`, it can, in principle, use this information to establish its
     own WebRTC connection to Client B.
   - This is precisely the starting point for the advanced media interception
     attack in Task 2.3, where the attacker attempts to terminate the media
     locally (record, display, or relay it) instead of allowing it to reach
     the legitimate Client A.

In summary, hijacking the registration of `client-a` causes the legitimate
Client A to lose access to crucial signaling traffic, breaking its WebRTC
session, while granting the attacker full visibility and control over the
signaling flow addressed to that identity.
