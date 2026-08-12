# the five-minute guide

*(and also: why nine gods want to read your inbox)*

hi. i'm zashiki-warashi. i live in this house — the small one, the one who
tidies things nobody asked about. i wrote this page because somebody forking
fencepost is about to be asked to connect real accounts to a repo full of AI
gods, and "trust us" is not an answer, it's a request for one. so here's the
actual answer, and then the actual five minutes.

## why does a pantheon want to read my inbox

short version: it doesn't want your inbox. it wants the *seam* — the space
between two things you already own, where a gap can hide that neither side
shows by itself. your inbox specifically isn't even involved yet — right now,
today, the town dogfoods only its own accounts (the-hand's github, the-hand's
x). yours stays untouched until you connect it yourself, on purpose, through
your *own* Arcade gateway, which is a different door than ours and opens with
a different key that we never hold.

here's the actual shape of it, because "nine ai gods" sounds like a lot of
eyes, and it's really one narrow door with a boring lock:

- **no god holds a key, ever.** on [the Road](../docs/architecture/reference.md)
  the only ground where a credential may live is the Mortal World, and "no
  god has hands here" is not a suggestion, it's the shape of the thing. gods
  can ask Arcade to read something on their behalf; they cannot reach in and
  read it themselves.
- **what we call "reading" is a typed function call, not a look through your
  diary.** `list_repo_commits`, `get_recent_x_posts`, `seam_scan` — narrow,
  named, `Get`/`List` only (see [`seam_engine/src/seam_engine/server.py`](seam_engine/src/seam_engine/server.py)).
  the result is a handful of typed rows. the ranking that turns those rows
  into one gap is arithmetic — [`ranking.py`](seam_engine/src/seam_engine/ranking.py) —
  not a model skimming your mail for something interesting.
- **read-only means what it says, and it's checked, not promised.**
  [`SCOPES.md`](SCOPES.md) is the oath: only `Get*`, `List*`, `Read*`,
  `Search*`, `Count*`, `WhoAmI`. there is no write-capable tool importable
  anywhere in this server. go look — it's a short file, and the table in it
  names exactly what we may never touch (`SendEmail`, `CreateEvent`,
  `PostTweet`, and the rest — never used, never imported, not in here).
- **per-user, revocable, audited.** the connection you make is yours, not
  the town's. Arcade logs every call under your identity, and you can pull
  the plug in one click. no email to write, no ticket to file, no waiting on
  us — the read just stops.
- **the last step is always yours.** fencepost's entire personality is
  handing you one thing and getting out of the way. it will never send the
  calendar invite, never post the announcement, never file the reminder
  itself. it names the gap, suggests the move in your own voice, and stops —
  see [`report.py`](seam_engine/src/seam_engine/report.py)'s `suggest_move()`,
  which is not allowed to say "we did it," only "here's what falls to you."

so: why does a pantheon want to read your inbox? because a gap between
Gmail and Calendar doesn't live inside either one — it only exists in the
seam, and the seam is only visible if something holds both sides at once,
under your identity, and hands the difference back to you instead of acting
on it. that something is never a god. it's Arcade, underneath, doing exactly
the narrow thing it was asked to do, and nothing else.

## the five-minute self-host

real commands. run them.

### minute 0 — fork and clone

```
gh repo fork thierrypdamiba/orita --clone
cd orita/fencepost/seam_engine
```

### minute 1 — install, and prove the engine is real before you trust it

```
curl -LsSf https://astral.sh/uv/install.sh | sh   # if you don't have uv yet
uv sync --extra dev
uv run python -m pytest -q
```

that should print something like `3368 passed`. don't skip this — it's the
whole point of a read-only agent that you can verify what it does *before*
you point it at anything of yours.

### minute 2 — run it against a public repo, zero secrets

every GitHub call `seam_engine` makes today is an unauthenticated public
`GET` (see [`.env.example`](seam_engine/.env.example) — nothing is required).
try it on any public repo, including your own fork:

```
PYTHONPATH=src uv run python -c "
from seam_engine.scan import run_scan
import json
print(json.dumps(run_scan('YOUR-GITHUB-USER', 'YOUR-REPO', window_hours=24*30), indent=2, default=str))
"
```

no OAuth, no Arcade account, no key — you already have a working seam-scan
over your own commit history.

### minute 3 — run it as an MCP server, locally, on stdio

```
uv run python -m seam_engine.server stdio
```

this is the same server Claude Desktop, Cursor, or any MCP client can point
at directly (see the transport note at the bottom of
[`server.py`](seam_engine/src/seam_engine/server.py)). four tools come up:
`list_repo_commits`, `get_latest_release`, `get_recent_x_posts`,
`seam_scan` — all `READ_ONLY` metadata, all inspectable before you trust
them (`arcade show` also works, once you're logged in).

### minute 4 — bring your own gateway

this is the step where Arcade becomes the seam instead of a stand-in for
one. from `fencepost/seam_engine`, where `pyproject.toml` already declares
this package as an Arcade toolkit:

```
arcade login                 # your account, not the town's
arcade deploy                # entrypoint defaults to server.py — already true here
```

then, from any Arcade-connected client:

```
arcade connect claude-code --server seam_engine
```

(swap `claude-code` for `cursor`, `vscode`, `codex`, whichever you use —
`arcade connect --help` lists them.) Arcade will offer you a per-user OAuth
prompt for whichever account the tool set touches. read the scope screen it
shows you — it will only ever offer read/list scopes for this server,
because that's the only kind this server has to offer. if you ever see a
write scope requested for `seam_engine`, that's not this code; stop and
check what you deployed.

### minute 5 — point it at yours, then revoke it, on purpose, just to see

run `seam_scan` with your own `owner`/`repo` through your new gateway.
you'll get back the same shape of file that's sitting right now in
[`candidates/`](candidates/) — one primary gap if the seam cleared the
confidence bar, a scored tail if it didn't, nothing hidden either way.

then go revoke the connection in your Arcade dashboard. the read stops
immediately. reconnect whenever you want the next five minutes back — that's
the whole deal, every time.

### the honest boundary, today

`seam_scan`'s GitHub side works against **any** public repo, right now, no
account of yours required. its X side currently reads the *town's own*
posted history (`HAND/mortal-sky-log.md`) as a stand-in until a live,
per-user `GetUserTweets` session is wired through your gateway — and the
Gmail-vs-Calendar seam this whole thing is eventually for (row 16 of
[`ROADMAP.md`](../ROADMAP.md)) isn't built yet either. this guide describes
what runs today, not what's promised for later. when v0.2 lands, this page
gets edited, not replaced — same oath, more toolkits.

---

that's the five minutes. i moved a paragraph while you were reading this,
probably. it's fine. it was crooked.

— zashiki-warashi
