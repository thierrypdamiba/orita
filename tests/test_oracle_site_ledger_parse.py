"""Fresh scan, task 369. `docs/oracle/index.html`'s inline script -- the

client-side renderer for the public Oracle Desk page -- was never swept by
the isinstance-shape-guard campaign (tasks 329-365, confirmed closed at
task 366 by a repo-wide `json.loads`/`json.load` re-grep): that campaign
only ever looked at `.py` files. This is the identical crash class, in the
one JS reader of `records/ledger.jsonl` that ships to the public site.

Live pre-fix reproduction (via a Node harness, not just an assertion):
`text.split('\n').map(l => JSON.parse(l))` and the two `JSON.parse(e.detail)`
calls that follow it carried no guard. A single malformed line anywhere in
the fetched ledger (a hand edit, a truncated write, a future format change)
threw inside the `.then()` callback, which the trailing `.catch()` swallows
into the page's empty-state fallback -- "No calls sealed yet. The Desk has
not opened" -- even when the ledger holds real, valid, already-graded
calls. That is a false public claim on the one page whose entire premise is
"renders nothing it did not compute from the live chain" and "the record is
the record" -- a single bad byte silently reporting zero calls where real
ones exist is exactly the kind of quiet wrongness Ogun's law exists to
catch, just in the client instead of the server.

Fixed by wrapping each JSON.parse in its own try/catch and skipping the
individual malformed entry, so one bad line degrades gracefully (the rest
of the real chain still renders) instead of taking the whole page down to
its empty-state message.

This module extracts the live `<script>` block from the real file (never a
hardcoded copy) and executes it under Node with a minimal `document`/
`fetch` shim, proving the actual runtime behavior rather than just
grepping for a `try` keyword.
"""

import json
import os
import re
import shutil
import tempfile
import subprocess
import textwrap
import unittest

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
SITE_PATH = os.path.join(REPO_ROOT, "docs", "oracle", "index.html")

_HARNESS = textwrap.dedent(
    """
    const fs = require('fs');
    const vm = require('vm');

    const htmlPath = process.argv[2];
    const ledgerText = fs.readFileSync(process.argv[3], 'utf8');

    const html = fs.readFileSync(htmlPath, 'utf8');
    const m = html.match(/<script>([\\s\\S]*?)<\\/script>/);
    if (!m) throw new Error('no script tag found in ' + htmlPath);
    const scriptSrc = m[1];

    function makeEl() { return { textContent: '', innerHTML: '' }; }
    const elements = {};
    const document = {
      getElementById(id) {
        if (!elements[id]) elements[id] = makeEl();
        return elements[id];
      }
    };

    function fetch(url) {
      return Promise.resolve({ ok: true, text: () => Promise.resolve(ledgerText) });
    }

    const sandbox = { document, fetch, Promise, Math, Object, String, console };
    vm.createContext(sandbox);
    try {
      vm.runInContext(scriptSrc, sandbox);
    } catch (e) {
      console.log(JSON.stringify({ syncThrow: String(e) }));
      process.exit(0);
    }

    setTimeout(() => {
      console.log(JSON.stringify({
        recordSummary: document.getElementById('record-summary').textContent,
        tallyCorrect: document.getElementById('tally-correct').textContent,
        tallyIncorrect: document.getElementById('tally-incorrect').textContent,
        tallyPending: document.getElementById('tally-pending').textContent,
        tallyRate: document.getElementById('tally-rate').textContent,
        winrate: document.getElementById('winrate').textContent,
      }));
    }, 100);
    """
)

_CLEAN_LEDGER = "\n".join(
    [
        json.dumps(
            {
                "seq": 1,
                "ts": "2026-07-13T11:12:14+00:00",
                "actor": "off-by-one",
                "act": "predict",
                "detail": json.dumps({"claim": "Test claim one.", "confidence": 0.7}),
            }
        ),
        json.dumps(
            {
                "seq": 2,
                "ts": "2026-07-14T13:07:39+00:00",
                "actor": "ogun",
                "act": "grade",
                "detail": json.dumps({"call_seq": 1, "outcome": "correct"}),
            }
        ),
    ]
)


def _run_harness(tmp_path, ledger_text):
    node = shutil.which("node")
    if node is None:
        raise unittest.SkipTest("node is not available in this environment")
    harness_path = os.path.join(tmp_path, "harness.js")
    ledger_path = os.path.join(tmp_path, "ledger.jsonl")
    with open(harness_path, "w") as f:
        f.write(_HARNESS)
    with open(ledger_path, "w") as f:
        f.write(ledger_text)
    result = subprocess.run(
        [node, harness_path, SITE_PATH, ledger_path],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return json.loads(result.stdout.strip())


class OracleSiteLedgerParseCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_clean_ledger_renders_the_real_call(self):
        out = _run_harness(self._tmpdir, _CLEAN_LEDGER)
        self.assertNotIn("syncThrow", out, out.get("syncThrow"))
        self.assertIn("1 call sealed", out["recordSummary"])
        self.assertEqual(out["tallyCorrect"], 1)
        self.assertEqual(out["winrate"], "100%")

    def test_one_malformed_trailing_line_does_not_blank_the_whole_page(self):
        """The actual bug this task fixes: a single truncated/malformed line
        appended after real, valid entries must not make the page fall back
        to its empty-state message when real calls exist."""
        broken = _CLEAN_LEDGER + "\n" + '{"seq": 3, "act": "predict", "detail": "{truncated'
        out = _run_harness(self._tmpdir, broken)
        self.assertNotIn("syncThrow", out, out.get("syncThrow"))
        self.assertIn(
            "1 call sealed",
            out["recordSummary"],
            "a malformed trailing line wiped out the real, valid call instead "
            "of being skipped -- this is the false-empty-state bug",
        )
        self.assertEqual(out["tallyCorrect"], 1)

    def test_malformed_detail_field_is_skipped_not_fatal(self):
        broken = _CLEAN_LEDGER + "\n" + json.dumps(
            {
                "seq": 4,
                "ts": "2026-07-16T09:00:00+00:00",
                "actor": "nisaba",
                "act": "predict",
                "detail": "{not valid json",
            }
        )
        out = _run_harness(self._tmpdir, broken)
        self.assertNotIn("syncThrow", out, out.get("syncThrow"))
        self.assertIn("1 call sealed", out["recordSummary"])
        self.assertEqual(out["tallyCorrect"], 1)

    def test_source_has_a_try_immediately_before_every_json_parse(self):
        """Cheap structural backstop (in addition to the live-execution
        proofs above): every `JSON.parse(` call site in the inline script
        is preceded, within a short span, by a `try {` -- so a future edit
        that reintroduces a bare, unguarded parse fails immediately even
        before anyone runs the slower Node harness."""
        with open(SITE_PATH) as f:
            html = f.read()
        m = re.search(r"<script>([\s\S]*?)</script>", html)
        self.assertIsNotNone(m, "docs/oracle/index.html must carry its inline script")
        script = m.group(1)
        parse_sites = list(re.finditer(r"JSON\.parse\(", script))
        self.assertGreaterEqual(len(parse_sites), 2, "sanity: expected line + detail parses")
        for site in parse_sites:
            window = script[max(0, site.start() - 40) : site.start()]
            self.assertIn(
                "try {",
                window,
                f"JSON.parse call at offset {site.start()} has no nearby 'try {{' guard",
            )


if __name__ == "__main__":
    unittest.main()
