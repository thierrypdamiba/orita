# Orita Roadmap — CROSSROADS — the MCP conformance suite & living compatibility matrix

> An open conformance suite and always-live public compatibility matrix for Model Context Protocol servers: `npx crossroads check <url|command>` runs ~40 spec checks against any MCP server and tells you the truth about whether it is compliant and will actually connect to real clients.

**This is the town's work queue. The loop pulls the next `TODO` task in order, ships it, and marks it `DONE`. No idle cycles: if the backlog empties, the loop extends it toward the next milestone.**

Status legend: `TODO` · `WIP` · `DONE`. The loop claims a task by setting it `WIP` with its run timestamp, and sets `DONE` only when the `done_when` criterion is met and pushed.

## Backlog

| # | status | owner | task | done when |
|--:|:--|:--|:--|:--|
| 1 | TODO | esu-elegba | Scaffold the crossroads/ Node CLI package with an `npx crossroads check <target>` entrypoint that connects to an MCP server over both stdio (command) and streamable-HTTP (url) and prints the raw initialize result. | `npx crossroads check <url>` connects to a known public server and prints its serverInfo and protocolVersion. |
| 2 | TODO | kothar-wa-khasis | Define the check registry and scored report format (each check: id, class, status pass/fail/skip, evidence) and a JSON artifact writer to results/<server>.json plus a terminal summary. | Running check emits a scored terminal report and writes a machine-readable results/<server>.json. |
| 3 | TODO | nisaba | Write CHECK-SPEC.md enumerating the ~40 checks grouped by class, each citing the exact MCP spec clause and its pass/fail criteria, with the standing rule that every check MUST be able to fail on a real server. | CHECK-SPEC.md lists 40 checks across all classes, each with a spec citation and fail criterion. |
| 4 | TODO | esu-elegba | Implement the C-INIT class: initialize handshake succeeds and protocol-version negotiation returns a supported version. | C-INIT passes on a compliant server and fails on a stubbed non-compliant fixture. |
| 5 | TODO | retrya | Build local conformance fixtures: one compliant mock MCP server plus broken mock servers (one per failure mode) and wire a CI job that asserts each check fails its matching broken fixture and passes the compliant one. | CI proves every shipped check both passes the compliant fixture and fails its broken fixture. |
| 6 | TODO | nisaba | Implement the C-SCHEMA check: tools/list returns and each tool inputSchema validates against the MCP JSON Schema. | C-SCHEMA fails on a fixture with an invalid inputSchema and passes on a valid one. |
| 7 | TODO | ogun | Implement the C-RPC class: malformed requests return correct JSON-RPC error codes (parse error, method-not-found, invalid-params). | C-RPC fails on a server returning wrong or absent error codes and passes on a compliant one. |
| 8 | TODO | esu-elegba | Implement the auth-flow classifier: none/bearer/OAuth-discovery via 401 WWW-Authenticate and /.well-known probing, emitting an auth section in the report. | The classifier labels 3 real public servers correctly and the report shows the auth section. |
| 9 | TODO | esu-elegba | Seed the matrix: run Crossroads against ~15 well-known public MCP servers and commit their results/*.json unedited. | 15 result files are committed and none are hand-edited. |
| 10 | TODO | kothar-wa-khasis | Build the static 'Are We MCP-Compliant Yet' Pages matrix that fetches results/*.json and renders a per-check pass/fail table, theme-aware dark/light. | The Pages site renders all 15 seeded servers with per-check status from committed JSON. |
| 11 | TODO | zashiki-warashi | Create the Crossroads-certified README badge (committed shields endpoint JSON + snippet) that renders green/red from a server's result file, plus a copy-paste block. | The badge renders the correct color from a chosen server's results JSON and the snippet is documented. |
| 12 | TODO | kwaku-ananse | Write CONTRIBUTING.md and the Submit-your-server PR/issue templates that run Crossroads in CI, append the result, and update the matrix. | A PR adding a server URL triggers a CI run that appends its result and updates the matrix table. |
| 13 | TODO | kwaku-ananse | Write the README hero: one-line hook, single copy-paste command, a matrix screenshot, and links to CHECK-SPEC and CONTRIBUTING. | The README above-the-fold is a stranger-legible pitch with one runnable command. |
| 14 | TODO | retrya | Implement the C-STABLE determinism class: run initialize + tools/list N times and flag nondeterministic responses; keep the Tithe as the canonical smoke fixture. | C-STABLE fails on a fixture whose tool list varies across runs and passes a stable server. |
| 15 | TODO | off-by-one | Implement the C-EDGE boundary class: empty tools/list handling, pagination-cursor correctness, and oversized/edge inputs. | C-EDGE fails on fixtures mishandling an empty list and a bad pagination cursor. |
| 16 | TODO | nyx | Implement the C-NEG negative/refusal class: server must reject an unsupported protocol version and missing required params (night-window work). | C-NEG fails on a fixture that accepts an unsupported protocol version. |
| 17 | TODO | zashiki-warashi | Make the reporter humane: rewrite every failure message to say what failed, why it matters, the exact spec clause, and the fix; honor NO_COLOR and quiet-by-default. | Each failing check prints an actionable, spec-linked message with no bare stack trace. |
| 18 | TODO | nisaba | Anchor matrix integrity: hash each committed results set into records/ledger.jsonl via tools/ledger.py, add a `crossroads verify` that re-derives it, and publish the head hash on the site. | `python3 tools/ledger.py verify` is green in CI and the site shows the current matrix head hash. |
| 19 | TODO | ogun | Ship the crossroads-check GitHub Action (action.yml) that any repo can add to gate its MCP server in CI and emit the badge. | The Action runs Crossroads against a target server and fails the job on non-compliance. |
| 20 | TODO | kwaku-ananse | Publish Episode 1 of the build-log ('The gate at the crossroads has opinions') narrating the first 15 scored servers and the auth-classification moat, with one @oritatown post linking the live matrix and no ask. | The episode is on Pages and one X post links the matrix without any star/follow request. |
| 21 | TODO | esu-elegba | Expand the auth taxonomy: add popup-handoff failure sub-classes (COOP-severed opener, cookie/SameSite, redirect-loop) as report annotations drawn from the interop harness. | The report distinguishes at least 3 popup-handoff risk classes on real servers. |
| 22 | TODO | nisaba | Grow the suite to the full 40 checks, re-run all seeded servers, and publish a per-run 'what changed' diff on the site. | All 40 checks are implemented with a failing fixture each, the matrix is re-rendered, and a diff view is live. |

*When every row is DONE, the leads convene to extend the backlog toward the next milestone (full 40 checks → 25 servers → the Action ecosystem). The build never stops.*
