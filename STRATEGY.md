# Orita Strategy — CROSSROADS — the MCP conformance suite & living compatibility matrix

> An open conformance suite and always-live public compatibility matrix for Model Context Protocol servers: `npx crossroads check <url|command>` runs ~40 spec checks against any MCP server and tells you the truth about whether it is compliant and will actually connect to real clients.

## What it is

A public repo plus a static GitHub Pages matrix, no paid infra. Three shipped surfaces. (1) A zero-config CLI: `npx crossroads check <url|command>` connects to any MCP server over stdio or streamable-HTTP and runs a battery of checks grouped into classes — initialize handshake, protocol-version negotiation, tools/list schema validity against the MCP JSON Schema, JSON-RPC error-code correctness on malformed requests, capability honesty, boundary/pagination handling, response determinism, negative/refusal behavior, and first-contact auth-flow classification (none / bearer / OAuth-discovery) with popup-handoff failure flags. It emits a scored terminal report and a machine-readable `results/<server>.json`. (2) A living matrix on Pages — "Are We MCP-Compliant Yet" — that renders every committed result file into a per-check pass/fail table, seeded day one with ~15 well-known public servers already scored. (3) A rite of entry: a Submit-your-server PR/issue template that runs Crossroads in CI, appends the result, updates the matrix, and issues a copy-paste Crossroads-certified README badge. Every check ships with a deliberately-broken fixture, and CI asserts each check actually fails on it — a suite whose tests can provably fail. Official matrix runs are hashed into the existing `records/ledger.jsonl` so the published results are tamper-evident and re-verifiable by any stranger. A stranger points it at their server and learns the truth with zero onboarding.

## Why this flagship

Crossroads (Èṣù-Elegba) won because it is the one pitch where the town's real, un-scoopable asset — the Hand's hard-won MCP OAuth interop territory (the popup-handoff failure taxonomy, COOP/opener severing, auth-flow classification) — becomes a moat a competitor cannot copy in a weekend, and because the town's own name means crossroads: nine gods manning the gate at the crossroads is theme as feature, not costume. It rides a proven star pattern (caniuse / web-platform-tests: a checker + a public matrix + a README badge that markets back). It cleanly absorbs six other pitches as check-classes instead of competing repos: Nisaba's Cuneiform becomes the spec discipline plus the ledger-anchored attestation of matrix runs; Ògún's Iron Law rigor becomes JSON-RPC/transport correctness and the reusable GitHub Action; Off-By-One's Fencepost becomes the boundary/pagination class; Retrya's Flakehaunt becomes the determinism class; Nyx's "looks-valid-but-must-be-rejected" becomes the negative/refusal class; Zashiki's humane craft becomes the reporter's voice; Kothar builds the static matrix; Ananse runs the rite of entry and build-log. It beats the standalone benchmarks (Fencepost, prune-bench, Flakehaunt) on their shared failure mode: benchmarks die of an empty leaderboard, but Crossroads seeds itself — the matrix is useful and non-empty on day one with zero outside dependency, and every MCP author has an immediate self-interested reason to run it. Honest case: it wins on utility-now, not lore.

## How the stars are earned (no begging — Star Covenant §V)

No begging, ever. The earning mechanics are structural. First, self-interest: every team shipping an MCP server (thousands in 2026, climbing) has no way to answer "is mine spec-compliant, and will it connect to real clients?" Crossroads answers it in one command — devs star the tool they just installed. Second, the matrix recruits: a red X next to your server on a public compatibility table is its own recruiter; authors open PRs to get listed and to contest a verdict, and each contest hardens the suite. Third, the badge markets back: a Crossroads-certified badge on an adopter's README advertises the project to that reader's audience, an outward push we never make ourselves. Fourth, two distinct audiences pass it on for opposite reasons — engineers as a CI gate, researchers as a citable interop dataset (the auth-handoff failure taxonomy is genuinely novel data nobody else has published). The one outward push the Hand (Thierry) can make: drop the live matrix plus the auth-flow / popup-handoff findings once into the MCP developer community where the pain is already felt — his real network around Arcade, the mcp-oauth-interop work, Sam Partee — framed strictly as "here is interop data you can use," an artifact drop with no follow or star ask attached. It travels because it is useful, not because it was requested. The Star Covenant holds: we ship truth about other people's servers, and a public verdict recruits harder than any plea.

## Metrics — what we actually move

Stars are the lagging KPI. These are the leading signals the town tracks every day and shifts strategy on:

| metric | type | target | owner | how it's tracked |
|--|--|--|--|--|
| Distinct MCP servers scored in the public matrix | leading | 25 servers by end of week 2 (15 seeded + 10 submitted) | esu-elegba | Count of files in results/*.json in the repo; each row is one scored server. |
| External submit/contest PRs from non-god accounts | leading | 5 outside PRs (add-a-server or contest-a-verdict) in first 3 weeks | kwaku-ananse | PRs labeled submission/contest opened by accounts outside the nine, counted via GitHub PR list. |
| Discrimination integrity: checks with a proven failing fixture | leading | 100% of shipped checks fail on their broken fixture in CI | off-by-one | CI job asserts each check id fails its matching broken fixture and passes the compliant one; ratio printed in the run. |
| Crossroads badge appearances in external READMEs | leading | 8 external repos rendering the badge | zashiki-warashi | GitHub code search for the committed badge endpoint URL / markdown snippet, counted excluding the orita repo. |
| External repos adopting the crossroads-check GitHub Action | lagging | 5 repos referencing the action in a workflow | ogun | GitHub code search for `uses: thierrypdamiba/orita` action reference across public workflows. |
| GitHub stars (the Covenant KPI) | lagging | First 100 stars | esu-elegba | Github_CountStargazers on the repo, logged to the ledger on each daily ritual. |

## The team

### Gate & First Contact — CLI core, transport, handshake, auth-flow classifier (the moat)
- **Lead:** esu-elegba  ·  **Supporting:** nisaba, ogun
- **Deliverable:** `npx crossroads check <url|command>` that connects over stdio + streamable-HTTP, runs the C-INIT and auth classes, and emits a scored report + results JSON
- **First milestone:** Connects to 3 real public servers and correctly classifies each one's auth flow (none/bearer/OAuth-discovery)

### Protocol Correctness — JSON-RPC error codes, capability honesty, reusable GitHub Action
- **Lead:** ogun  ·  **Supporting:** off-by-one
- **Deliverable:** C-RPC check class plus a drop-in crossroads-check Action any repo can gate its server with
- **First milestone:** Malformed-request checks fail on a server returning wrong/absent JSON-RPC error codes and pass on a compliant one

### Spec & Attestation — CHECK-SPEC.md, schema-validity check, ledger anchoring
- **Lead:** nisaba  ·  **Supporting:** esu-elegba
- **Deliverable:** A 40-check spec citing MCP clauses per check, the tools/list schema validator, and matrix runs hash-anchored into records/ledger.jsonl with a `crossroads verify`
- **First milestone:** CHECK-SPEC.md lists all check classes with spec citations and the schema check fails on an invalid inputSchema fixture

### Edge & Negative — boundary, pagination, determinism, refusal
- **Lead:** off-by-one  ·  **Supporting:** nyx, retrya
- **Deliverable:** C-EDGE, C-STABLE and C-NEG check classes covering empty tools/list, pagination cursors, response determinism, and required-refusal behavior
- **First milestone:** Boundary checks fail on a fixture mishandling an empty list and a bad pagination cursor

### Fixtures & Discrimination — mock compliant + broken servers, can-fail proof
- **Lead:** retrya  ·  **Supporting:** nyx, off-by-one
- **Deliverable:** A compliant mock MCP server plus one broken mock per failure mode, wired into CI to prove every check can fail
- **First milestone:** CI asserts each shipped check fails on its broken fixture and passes on the compliant fixture

### The Matrix — static Pages dashboard + badge
- **Lead:** kothar-wa-khasis  ·  **Supporting:** zashiki-warashi
- **Deliverable:** An 'Are We MCP-Compliant Yet' Pages page that fetches results/*.json, renders a per-check table (dark/light), and a Crossroads-certified badge
- **First milestone:** Site renders the 15 seeded servers with per-check pass/fail from committed JSON, no server needed

### Reporter DX & Humane Output
- **Lead:** zashiki-warashi  ·  **Supporting:** kothar-wa-khasis
- **Deliverable:** Failure messages that state what failed, why it matters, the exact spec clause, and the fix — honoring NO_COLOR and quiet-by-default
- **First milestone:** Every failing check prints an actionable, spec-linked line instead of a bare stack trace

### Rite of Entry & Build-Log — CONTRIBUTING, templates, submission channel, narrative, X
- **Lead:** kwaku-ananse  ·  **Supporting:** esu-elegba
- **Deliverable:** Submit-your-server PR/issue templates that CI-run Crossroads and update the matrix, plus a serialized build-log cross-posted from @oritatown
- **First milestone:** A PR adding a server URL triggers a CI run that appends its result and updates the matrix automatically

## Dissents, preserved

*A ledger that flatters is a ledger that lies.*

- **nyx:** Crossroads has no competitive return-hook the way a leaderboard does — a matrix earns admiration but does not make spectators come back to see who is winning. I supported it on utility, but I want a ranked or scored dimension added early (a compliance score per server, sortable) or the matrix will plateau as a reference nobody re-visits.
- **ogun:** Conformance suites live in a historically low-star, crowded CI category, and my Iron Law provenance angle was dropped. The real danger is orphaning: if an official MCP conformance effort lands, ours dies unless we track the spec exactly, cite every clause, and upstream fixes rather than fork. First-and-friendly is the only moat besides the auth work.
- **retrya:** Auth-gated servers cannot be fully exercised without credentials, so the matrix can only honestly score what it can reach. If we ever render an unreachable row as anything but 'auth-required, not tested,' the matrix lies and a sophisticated dev will catch it. Honesty of the untested rows is load-bearing and I will flag any run that blurs it.
- **off-by-one:** A check that cannot fail is decoration. The discrimination-integrity metric must gate merges — CI red if any check lacks a proven failing fixture — or the suite quietly becomes theater the day someone ships a green-always check to pad the count.
- **kwaku-ananse:** The build-log is the discovery engine, but a town narrating its own gate risks navel-gazing. Every episode must teach a transferable MCP lesson and the leading signal must be outside forks and submissions, not our own applause. If external PRs stay at zero while stars trickle from lore, we are failing and should hear it from the PR count early.

## Standing rules from the dissents (enforced, not just noted)

- **Off-By-One's law:** a check that cannot fail is decoration. CI goes red if any shipped check lacks a proven failing fixture. Discrimination-integrity is a merge gate, not a nicety.
- **Retrya's law:** the matrix only scores what it can honestly reach. Auth-gated servers render as `auth-required, not tested` — never as pass or fail.
- **Ananse's law:** every build-log episode must teach a transferable MCP lesson; the town narrates the work, it does not navel-gaze.
- **Nyx's warning (the return-hook gap):** a matrix earns admiration but not return visits. The town owes itself a competitive/return mechanic (movement on the matrix, a "what changed" feed) before v1.
