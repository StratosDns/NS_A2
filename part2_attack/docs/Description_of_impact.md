# “Description of impact on legitimate Client A”

After the attacker successfully registered as client-a, the signaling server associated the identifier client-a with the attacker’s WebSocket connection.
Subsequent signaling messages from Client B that were addressed to client-a were forwarded exclusively to the attacker and no longer delivered to the legitimate Client A.
In practice, this resulted in:

[video freezing / connection failing] on Client A’s browser,

[WebSocket disconnection / error logs] in the JavaScript console,

and an inability for Client A to renegotiate or resume the call.

The legitimate client remained unaware that its identity had been taken over: no explicit warning was shown in the UI. From the user’s perspective, the application simply “stopped working,” while the attacker transparently received all signaling messages intended for them.