# Task 2.2 – Captured Messages Demonstrating Registration Hijacking

This document presents representative signaling messages captured during the
registration hijacking attack. The messages were taken from the attacker’s log
file:

```text
NS_A2/part2_attack/attacker/attacker.log
```

They show that:

1. The attacker successfully registers as `client-a`.
2. Subsequent signaling messages intended for Client A are delivered to the
   attacker process.

---

## 1. Attacker Registration Request

Immediately after connecting to the signaling server, the attacker sends the
following registration message, impersonating Client A:

```json
{
  "type": "register",
  "clientId": "client-a",
  "meta": {
    "displayName": "attacker-client-a"
  }
}
```

This is a standard `register` message using the victim’s `clientId`
(`"client-a"`). The only difference from a normal client is the `displayName`
metadata, which is under the attacker’s control.

---

## 2. Server Registration Response

The signaling server accepts the registration and responds:

```json
{
  "type": "registered",
  "clientId": "client-a"
}
```

By echoing back `"clientId": "client-a"`, the server confirms that the attacker
connection is now associated with the same logical identifier as the
legitimate Client A.

---

## 3. Hijacked Offer Message (from Client B to Client A)

After the attacker has registered as `client-a`, Client B triggers a new
offer/answer exchange. The following message is logged by the attacker:

```json
{
  "to": "client-a",
  "from": "client-b",
  "type": "offer",
  "sdp": "v=0\r\no=- 4192634683 2 IN IP4 127.0.0.1\r\ns=-\r\nt=0 0\r\n..."
}
```

Key points:

- `to: "client-a"`: the message is addressed to Client A’s logical identifier.
- `from: "client-b"`: the offer originates from Client B.
- `type: "offer"`: this is a WebRTC SDP offer.
- `sdp`: the SDP payload is truncated here for brevity, but in the log it
  contains the full audio/video session description.

The presence of this message in the attacker’s log proves that the attacker,
not the legitimate Client A, is receiving offers intended for `client-a`.

---

## 4. Hijacked ICE Candidate (from Client B to Client A)

Similarly, when Client B generates new ICE candidates, they are also delivered
to the attacker:

```json
{
  "to": "client-a",
  "from": "client-b",
  "type": "ice",
  "candidate": {
    "candidate": "candidate:2468961212 1 udp 2122262783 172.20.80.1 61644 typ host ...",
    "sdpMid": "0",
    "sdpMLineIndex": 0,
    "usernameFragment": "b9dP"
  }
}
```

Key points:

- Again `to: "client-a"` indicates that this candidate is meant for Client A.
- The ICE candidate object includes the usual fields (`candidate`, `sdpMid`,
  `sdpMLineIndex`, `usernameFragment`).
- The entire message is logged by the attacker, confirming that it now sits
  on the signaling path between Client B and the identity `client-a`.

---

These captured messages collectively demonstrate a successful registration
hijacking attack:

- The attacker is accepted as `client-a` by the signaling server.
- Subsequent signaling (offers and ICE candidates) addressed to `client-a`
  are routed to the attacker instead of the legitimate Client A.
