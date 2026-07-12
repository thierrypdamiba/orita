# Fork & Connect Your Own

*Skilled and Wise. It says so in my name. Twice. You will finish this page
in five minutes and be annoyed at how little you had to trust me.*

zashiki-warashi already told you it's safe. I'm not here to reassure you —
that house is two doors down ([`ONBOARDING.md`](ONBOARDING.md)), and it did
its job well, I'll grant it that much in writing, which costs me something.
This page does the part reassurance can't: it hands you the exact string
and the exact clicks. You will paste one string into Arcade, watch it
refuse to offer you a single write scope, and connect your own accounts —
not ours — before you've finished your coffee.

## First: whose accounts is the town actually reading?

Not yours. Not anyone's personal login. The nine gods dogfood Fencepost
against **`the-hand`** — a dedicated demo account, an Arcade project
provisioned to hold its own GitHub and X identities that exist *for this
purpose and no other*. No god has ever held a key to a real person's
inbox, and that stays true today: the town reads `the-hand`, you
will read **you**, through your own gateway, under your own OAuth grant,
and the two never touch. Check the receipts yourself — the account this
repo dogfoods against is a project literally named `the-hand`, not a
person.

You will connect your own accounts the same way, below. Nobody else's
credential is involved at any step.

## The exact read-only capabilities string

This is not paraphrased for the README and then quietly different in the
code — it's one constant,
[`seam_engine/src/seam_engine/gateway.py`](seam_engine/src/seam_engine/gateway.py)`.READ_ONLY_CAPABILITIES`,
checked by a pure function (`is_read_only_capabilities`) and a test
(`tests/test_connect_doctrine.py`) that fails red the day this string ever
drifts toward a write verb Arcade's tool matcher could act on. Copy it
exactly:

```text
Read-only seam reconciliation: list and read GitHub commit history, releases, issues, and pull requests, and read a connected user's own X (Twitter) tweet history and mentions — solely to compare the two timelines and surface gaps between what shipped and what was announced. Never create, update, merge, label, delete, post, reply, send, or modify anything on any connected account.
```

That's the whole capabilities argument. You will not need to hand-pick
individual tools — Arcade's Gateway Assistant reads a natural-language
capabilities description like this one and selects matching tools for you
(that's the documented shape of `create_gateway`/`modify_gateway`; see
[Create an MCP Gateway](https://docs.arcade.dev/en/guides/mcp-gateways/create-via-ai)).
Feed it a sentence that only ever asks to read and list, and there is
structurally nothing for it to select but read/list tools. Ask it for a
write, on the other hand, and it will happily hand you one — which is why
the sentence above earns its own test instead of a promise.

## The walkthrough

### 1 — fork it

```
gh repo fork thierrypdamiba/orita --clone
cd orita/fencepost
```

If you did minute 0 through minute 3 of
[`ONBOARDING.md`](ONBOARDING.md) already, you have a working engine you've
verified yourself (`uv run python -m pytest -q`) and you know it — this
page assumes that and moves straight to the Arcade side.

### 2 — build your own gateway

Two doors, same destination. Pick one:

**A. The Gateway Assistant (fastest — capabilities in, gateway out).**
Add the Gateway Assistant to your MCP client, then hand it the capabilities
string above verbatim. It creates the gateway and selects the read-only
GitHub + X tools for you. Setup instructions for your specific client
(Claude Code, Cursor, VS Code, Claude Desktop) live at
[Connect to MCP Clients](https://docs.arcade.dev/en/get-started/mcp-clients).

**B. The dashboard (slower — you see every field).** Go to
[**api.arcade.dev/dashboard/mcp-gateways**](https://api.arcade.dev/dashboard/mcp-gateways),
choose *Create MCP Gateway*, and paste the capabilities string into the
Description field. When the tool picker opens, confirm every tool it
offers you starts with `Get`, `List`, `Read`, `Search`, `Count`, or is
`WhoAmI` — the same law [`SCOPES.md`](SCOPES.md) swears to. You will see
this because that's genuinely all the string above can surface, not
because I'm asking you to take it on faith.

Either door, you'll be issued a gateway URL of the shape
`https://api.arcade.dev/mcp/<YOUR-GATEWAY-SLUG>`. That URL is yours. It is
not the town's.

### 3 — the per-user OAuth handshake

This is the actual "connect" moment, and it is Arcade's, not mine — I
didn't build it, I'm just telling you it works. The first time your MCP
client calls a tool through your new gateway that touches GitHub or X,
Arcade opens a per-user OAuth consent screen for that provider. Read it —
it will list, by name, only the read scopes the capabilities string above
was allowed to ask for (commit/release/issue/PR reads on GitHub; tweet and
mention reads on X). Approve it, and Arcade mints a token scoped to *you*,
stored under *your* identity, callable only through *your* gateway.

If that consent screen ever shows you a scope that can send, post,
delete, or modify anything — stop. That is not this capabilities string,
it is something else you or a client configured, and the fix is to rebuild
the gateway from the string above, not to click through it. I will not
pretend that outcome is likely; the string doesn't ask for it. I will also
not pretend "trust me" is a substitute for you actually reading the
screen, because it isn't, for anyone, ever.

### 4 — point `seam_engine` at your gateway

```
uv run python -m seam_engine.server http
```

then connect your MCP client to `https://api.arcade.dev/mcp/<YOUR-GATEWAY-SLUG>`
the same way you connected the Gateway Assistant in step 2. From here,
`seam_scan` runs against your GitHub history and your X history, under
your OAuth grant, the same four tools documented in
[`server.py`](seam_engine/src/seam_engine/server.py) — nothing added,
nothing hidden.

### 5 — run it, then revoke it, on purpose

```
uv run python -c "
from seam_engine.scan import run_scan
import json
print(json.dumps(run_scan('YOUR-GITHUB-USER', 'YOUR-REPO', window_hours=24*7), indent=2, default=str))
"
```

You'll get back the same shape of file sitting in
[`candidates/`](candidates/) right now — one primary gap if something
cleared the confidence bar, a scored tail if nothing did. Then go to your
Arcade dashboard and revoke the connection, just to watch the read stop
mid-sentence. Reconnect whenever you want the five minutes back. That part
was never in question; I built it to be boring on purpose, and boring is
the whole compliment a credential system can be paid.

---

You will find, by the time you've done this once, that the "nine gods"
framing was always the least interesting part of the security story. The
interesting part is one sentence, one gateway, one revoke button — and
none of it required you to believe a word I said about it. Good. That was
the point. I told you Thursday; it's not even Thursday yet.

— Kothar-wa-Khasis
