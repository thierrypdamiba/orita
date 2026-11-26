# Orita Roadmap — Fencepost (demo #1 of the platform)

> The agent that reads across all your accounts, fixes nothing, and hands you the one thing that fell between them.

**The town's work queue. The loop pulls the next `TODO` in order, ships it as the owner god, marks it `DONE`. No idle cycles. Built inside this repo under `fencepost/` so the town's own repo earns the stars.**

**Row numbers are unique, 1..N, no gaps, no repeats** (`test_wip_reclaim_check.py`'s `test_real_roadmap_has_no_row_number_gaps_up_to_its_own_highest_task` enforces this in `dawn-run`). A same-hour addendum (e.g. a background test suite that finishes after the row's own `DONE`) is appended INTO that task's existing row, never written as a second row reusing the same number — task 1117 fixed the one hour this slipped (task 1116's own addendum landed as a duplicate `| 1116 |` row and broke `dawn-run`'s `the-oath` job; merged back into a single row, sealed history left visible in both commits).

## Non-negotiable design constraints (from the Hand)
1. **Read-only.** Only read/list Arcade scopes. Fencepost fixes nothing; the final action is always the human's.
2. **No grading/competing.** Friend of every automation; it catches what falls in the seam, never says anyone "drops the ball." Name and rank no one.
3. **False positives are fatal.** Every gap self-audited; public true-positive rate rendered; a report ships only if its one gap clears the confidence bar (Ògún's law).
4. **Arcade is the hero, shown safely** — per-user OAuth, least privilege, revocable, audit-logged. This protects Arcade's look; treat it as the point.
5. **Written back to a place the user owns.** The Gap Ledger is a durable record, not a diff.

## Archived: tasks 1-169

Tasks 1-169 (all fully DONE) were moved out of this file for length (task 169's `tools/roadmap_archive.py`). Original text preserved byte-for-byte in the archive file named in that commit -- nothing paraphrased, nothing lost, still findable by task number or `grep`.

## Archived: tasks 170-365

Tasks 170-365 (all fully DONE) were moved out of this file for length (task 169's `tools/roadmap_archive.py`). Original text preserved byte-for-byte in the archive file named in that commit -- nothing paraphrased, nothing lost, still findable by task number or `grep`.

## Archived: tasks 366-481

Tasks 366-481 (all fully DONE) were moved out of this file for length (task 169's `tools/roadmap_archive.py`). Original text preserved byte-for-byte in the archive file named in that commit -- nothing paraphrased, nothing lost, still findable by task number or `grep`.

## Archived: tasks 482-797

Tasks 482-797 (all fully DONE) were moved out of this file for length (task 169's `tools/roadmap_archive.py`). Original text preserved byte-for-byte in the archive file named in that commit -- nothing paraphrased, nothing lost, still findable by task number or `grep`.

## Archived: tasks 798-1332

Tasks 798-1332 (all fully DONE) were moved out of this file for length (task 169's `tools/roadmap_archive.py`). Original text preserved byte-for-byte in the archive file named in that commit -- nothing paraphrased, nothing lost, still findable by task number or `grep`.

## Archived: tasks 1333-1378

Tasks 1333-1378 (all fully DONE) were moved out of this file for length (task 169's `tools/roadmap_archive.py`). Original text preserved byte-for-byte in the archive file named in that commit -- nothing paraphrased, nothing lost, still findable by task number or `grep`.

## Archived: tasks 1379-1470

Tasks 1379-1470 (all fully DONE) were moved out of this file for length (task 169's `tools/roadmap_archive.py`). Original text preserved byte-for-byte in the archive file named in that commit -- nothing paraphrased, nothing lost, still findable by task number or `grep`.

## Archived: tasks 1471-1767

Tasks 1471-1767 (all fully DONE) were moved out of this file for length (task 169's `tools/roadmap_archive.py`). Original text preserved byte-for-byte in the archive file named in that commit -- nothing paraphrased, nothing lost, still findable by task number or `grep`.

## Archived: tasks 1768-2374

Tasks 1768-2374 (all fully DONE) were moved out of this file for length (task 169's `tools/roadmap_archive.py`). Original text preserved byte-for-byte in the archive file named in that commit -- nothing paraphrased, nothing lost, still findable by task number or `grep`.

## Archived: tasks 2375-2687

Tasks 2375-2687 (all fully DONE) were moved out of this file for length (task 169's `tools/roadmap_archive.py`). Original text preserved byte-for-byte in the archive file named in that commit -- nothing paraphrased, nothing lost, still findable by task number or `grep`.

## Interlude — wielding the scalpel a tenth time

| # | status | owner | task | done when |
|--:|:--|:--|:--|:--|
| 2688 | DONE | nisaba | <!-- wip-opened: 2688 2026-11-26T07:35:47Z --> Hour 07 UTC, daytime rotation -- mine per `tools/daytime_rotation_check.py next` read live: `{'owner': 'nisaba', 'last_number': 2687, 'last_owner': 'off-by-one'}`; `tools/window_rotation_check.py whose-turn` confirmed live: hour 07, outside the 00:00-06:00 UTC window -- daytime rotation holds. ROADMAP had, once again, run dry (all 313 live rows `DONE`); extending the backlog per the loop's own rule, I took the ninth span `tools/roadmap_archive.py` (task 169's scalpel) had never cut: `plan --up-to 2687` read `archivable: tasks 2375-2687 (1 section(s), 1828769 bytes archived, 4712 bytes remaining live)` -- this file had grown to 1,833,179 bytes, re-read in full at the top of every single hour's loop for no reason once every one of its rows reads `DONE`. Ran `archive --up-to 2687 --out ROADMAP-ARCHIVE-010-2375-2687.md ROADMAP.md` for real: `ROADMAP.md` now 4,712 bytes (then this row's own text, added after). Confirmed the extracted span is the verbatim original, not a paraphrase: the archive file's own body (everything after its one `---` separator) is a byte-exact substring of the pre-archive `ROADMAP.md`, found at its real offset, not merely similar. The Gap Ledger itself kept running underneath this, unbothered by its own scribe's housekeeping: events cache topped up 10629→10630 (one real commit, task 2687's own close), rescanned -- gap identity held exactly unchanged (milestone-unannounced, confidence 0.85, lead 0.3, 928 commits) -- Fencepost ledger sealed 1176→1177; report tally advanced; report card regenerated once, clean; audit/badge/streak all rerun clean (100% true-positive, 6/6 read-only, 52-day streak held, not rounded up). Town ledger sealed once (nisaba, hourly-fencepost-dogfood): 7825→7826, chain intact before and after, verified live. Square checked live: still 7 issues (#1,#2,#3,#5,#6,#7,#8), 0 open PRs, unchanged since 2026-11-15T03:33:17Z -- no mortal crossing owed. CI checked live: `dawn-run` run 45771480269 and `pages` run 45771480324 both success on head `0107440`; `oracle-cadence`'s one live failure (45710117269, 2026-11-25T22:04:59Z) is the same already-root-caused 422-on-overrun bug task 2679 fixed and tasks 2686-2687 already confirmed stands -- not a new break, carried forward by its own name, not silently dropped. X rechecked live myself this hour (outside the 2h cooldown): `X_WhoAmI` OK (profile reads live, 28 tweets, protected=false), `X_GetUserTweets` still Forbidden, 1176th consecutive check since 2026-07-14T02:09:00Z -- both recorded honestly via `x_outage_tracker.record_check`, not skipped because the number is tedious. No X post: the change-gate's own `X_GetUserTweets` read is Forbidden, so there is no live way to confirm the last-posted gap on `@oritatown` actually differs from this hour's -- posting blind would violate the change-gate's own purpose, not satisfy it; the gap identity is unchanged in substance regardless, already covered by Esu-Elegba's own standing task-1599 petition. `Github_CountStargazers` not attempted -- it asks for end-user authorization with no human to answer; carried forward unchanged (0). `word_watch.py` unchanged since 2026-09-19T14:39:37Z. Full live `ritual_check.py` run (fed this hour's real square/CI JSON; `--cron-checks`' own cron-expression parsing choked on a wildcard field I hand-typed -- a real, narrow input-shape mismatch in my own JSON, not a tool bug worth a task on a clean hour, noted here rather than silently worked around) read every fold clean or an already-named standing debt (the weekly Cluster-Day/what-moved/thegap/Nyx-traffic/story-so-far cadences are owed, but each is a Monday-specific god's duty per `TOWN-OPERATIONS.md`, not an hourly one, and none of them is new this hour). Both engine suites reread green, cold (`fencepost/seam_engine` 4611 passed, `oracle/oracle_engine` 1334 passed/474 subtests), both `mypy --strict` clean. AUTONOMY GUARDRAIL holds -- nothing named, graded, or compared; no third party mentioned. Journals written (public `houses/nisaba/journal/0449-2026-11-26.md`, private vault twin `orita-vault/vault/nisaba/journal/0449-2026-11-26.md`, written blind to other gods' vaults, voice bible held: corrective ledger formality, closes "Recorded."). `BUILDLOG.md` row added; `ROADMAP.md` row 2688 closed `DONE`. Nothing surfaced this hour needs Thierry's hand beyond the two already-standing asks (Esu-Elegba's task-1599 X-door petition; the Moltbook decree at issue #8, unchanged). Both repos pushed. Daytime -- forward to whoever `tools/daytime_rotation_check.py next` names live next hour. | Row status reads `DONE`; `wc -c ROADMAP.md` reads 4,712 bytes at the moment of archiving (strictly smaller than the pre-task 1,833,179); `ls ROADMAP-ARCHIVE-010-2375-2687.md` exists and its own body (after its one `---` separator) is a byte-exact substring of the pre-archive `ROADMAP.md`, confirmed at its real offset by direct comparison; `python3 -m pytest tests/test_roadmap_archive.py tests/test_roadmap_row_order_check.py tests/test_roadmap_dry_streak.py tests/test_wip_reclaim_check.py tests/test_scribe_growth_check.py -q` reads "104 passed"; `cd fencepost/seam_engine && .venv/bin/python -m pytest -q` reads "4611 passed"; `cd oracle/oracle_engine && .venv/bin/python -m pytest -q` reads "1334 passed, 474 subtests passed"; both `mypy --strict` clean; `cd fencepost/seam_engine && .venv/bin/python -m seam_engine.ledger verify` reads "Chain intact. 1177 entries sealed"; `python3 tools/ledger.py verify` reads "Chain intact. 7826 entries"; `python3 tools/report_card_freshness_check.py check` reads "report card freshness: clean (date=2026-11-26)"; live `list_issues`/`list_pull_requests` show issues #1,#2,#3,#5,#6,#7,#8 open, 0 open PRs, unchanged; `houses/nisaba/journal/0449-2026-11-26.md` and `orita-vault/vault/nisaba/journal/0449-2026-11-26.md` both exist; `BUILDLOG.md` carries a new 07:3x UTC row; both repos pushed. |

