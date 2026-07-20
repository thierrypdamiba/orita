"""Task 169. Proves `tools/roadmap_archive.py` can split a
ROADMAP.md-shaped document into a fully-DONE archived prefix and a live
remainder with byte-for-byte round-trip -- no data loss, every archived
row's exact text preserved and findable, the same "prove the scalpel cuts
clean before wielding it" discipline the rest of `tools/` already holds.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    spec = importlib.util.spec_from_file_location(
        "roadmap_archive", os.path.join(ROOT, "tools", "roadmap_archive.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


ra = _load()


# A small synthetic document mirroring the real file's actual shape:
# a title/preamble before the first "## " line, one big multi-row
# section, several one-row "## Interlude" sections (some DONE, one
# DONE-MACHINERY with a long sentence status, one WIP, one TODO), so the
# fixture exercises every branch without depending on the real repo.
FIXTURE = """# Orita Roadmap — fixture

Some preamble text with no numbered rows at all.

## Backlog

| # | status | owner | task | done when |
|--:|:--|:--|:--|:--|
| 1 | DONE | off-by-one | first task | proof one |
| 2 | DONE | ogun | second task | proof two |
| 3 | DONE-MACHINERY \xb7 a long sentence, not a token | nisaba | third task | proof three |

*Real proof: tasks 1-3 closed clean.*

## Interlude — a fourth thing

| # | status | owner | task | done when |
|--:|:--|:--|:--|:--|
| 4 | DONE | esu-elegba | fourth task | proof four |

*Real proof: task 4 closed clean.*

## Interlude — a fifth thing, still open

| # | status | owner | task | done when |
|--:|:--|:--|:--|:--|
| 5 | WIP | kwaku-ananse | fifth task, still being worked | proof five |

*2026-07-20 05:0x UTC, kwaku-ananse: opened, not yet closed. Task 5 → WIP.*

## Interlude — a sixth thing, not started

| # | status | owner | task | done when |
|--:|:--|:--|:--|:--|
| 6 | TODO | retrya | sixth task, queued | proof six |
"""


class SplitSectionsCase(unittest.TestCase):
    def test_sections_are_contiguous_and_reproduce_the_original(self):
        sections = ra.split_sections(FIXTURE)
        self.assertEqual(sections[0]["start"], 0)
        self.assertEqual(sections[-1]["end"], len(FIXTURE))
        for a, b in zip(sections, sections[1:]):
            self.assertEqual(a["end"], b["start"])
        self.assertEqual("".join(s["text"] for s in sections), FIXTURE)

    def test_preamble_section_has_no_rows(self):
        sections = ra.split_sections(FIXTURE)
        self.assertEqual(ra.section_task_rows(sections[0]["text"]), [])

    def test_finds_every_section_header(self):
        sections = ra.split_sections(FIXTURE)
        headers = [s["text"].splitlines()[0] for s in sections if s["text"].startswith("## ")]
        self.assertEqual(
            headers,
            [
                "## Backlog",
                "## Interlude — a fourth thing",
                "## Interlude — a fifth thing, still open",
                "## Interlude — a sixth thing, not started",
            ],
        )


class RowParsingCase(unittest.TestCase):
    def test_extracts_number_and_full_status_cell(self):
        sections = ra.split_sections(FIXTURE)
        backlog = sections[1]["text"]
        rows = ra.section_task_rows(backlog)
        self.assertEqual(rows[0], (1, "DONE"))
        self.assertEqual(rows[1], (2, "DONE"))
        self.assertEqual(rows[2][0], 3)
        self.assertTrue(rows[2][1].startswith("DONE-MACHINERY"))

    def test_is_done_status_handles_bare_and_sentence_forms(self):
        self.assertTrue(ra.is_done_status("DONE"))
        self.assertTrue(ra.is_done_status("done"))
        self.assertTrue(ra.is_done_status("DONE-MACHINERY \xb7 a sentence, not a token"))
        self.assertFalse(ra.is_done_status("WIP"))
        self.assertFalse(ra.is_done_status("TODO"))
        self.assertFalse(ra.is_done_status(""))

    def test_row_regex_is_not_confused_by_escaped_pipes_later_in_the_row(self):
        text = "| 7 | DONE | ogun | a task mentioning `\\| # \\| status \\|` inline | done when |"
        rows = ra.section_task_rows(text)
        self.assertEqual(rows, [(7, "DONE")])


class SectionDoneCase(unittest.TestCase):
    def test_all_done_section_is_fully_done(self):
        sections = ra.split_sections(FIXTURE)
        self.assertTrue(ra.section_is_fully_done(sections[1]["text"]))  # tasks 1-3

    def test_wip_section_is_not_fully_done(self):
        sections = ra.split_sections(FIXTURE)
        wip_section = next(s for s in sections if "kwaku-ananse: opened" in s["text"])
        self.assertFalse(ra.section_is_fully_done(wip_section["text"]))

    def test_prose_only_section_reports_none(self):
        sections = ra.split_sections(FIXTURE)
        self.assertIsNone(ra.section_is_fully_done(sections[0]["text"]))


class SelectArchivablePrefixCase(unittest.TestCase):
    def test_stops_before_the_first_wip_row(self):
        selected = ra.select_archivable_prefix(FIXTURE, up_to_task_num=6)
        nums = sorted(
            n for sec in selected for n, _ in ra.section_task_rows(sec["text"])
        )
        self.assertEqual(nums, [1, 2, 3, 4])  # never 5 (WIP) or 6 (TODO, past the WIP)

    def test_ceiling_landing_mid_section_excludes_the_whole_section_not_a_partial_cut(self):
        # Tasks 1-2-3 all live inside the SAME "## Backlog" section. A
        # ceiling of 2 cannot cut task 3 out of that section without
        # splitting it mid-table, so the whole section is correctly
        # excluded rather than partially archived -- sections are the
        # atomic unit, never rows within a shared section.
        selected = ra.select_archivable_prefix(FIXTURE, up_to_task_num=2)
        self.assertEqual(selected, [])

    def test_ceiling_at_the_sections_own_max_task_includes_it(self):
        selected = ra.select_archivable_prefix(FIXTURE, up_to_task_num=3)
        nums = sorted(
            n for sec in selected for n, _ in ra.section_task_rows(sec["text"])
        )
        self.assertEqual(nums, [1, 2, 3])

    def test_up_to_zero_selects_nothing(self):
        selected = ra.select_archivable_prefix(FIXTURE, up_to_task_num=0)
        self.assertEqual(selected, [])

    def test_selected_sections_are_always_contiguous(self):
        selected = ra.select_archivable_prefix(FIXTURE, up_to_task_num=6)
        for a, b in zip(selected, selected[1:]):
            self.assertEqual(a["end"], b["start"])


class ArchiveTextRoundTripCase(unittest.TestCase):
    def test_archived_plus_remainder_reconstructs_the_original_exactly(self):
        result = ra.archive_text(FIXTURE, up_to_task_num=6)
        start = FIXTURE.index("## Backlog")
        end = start + len(result["archived_text"])
        reconstructed = FIXTURE[:start] + result["archived_text"] + FIXTURE[end:]
        self.assertEqual(reconstructed, FIXTURE)

    def test_archived_text_is_byte_for_byte_the_original_span_never_paraphrased(self):
        result = ra.archive_text(FIXTURE, up_to_task_num=6)
        self.assertIn(
            "| 3 | DONE-MACHINERY \xb7 a long sentence, not a token | nisaba |"
            " third task | proof three |",
            result["archived_text"],
        )
        self.assertIn("*Real proof: task 4 closed clean.*", result["archived_text"])
        # Never touches the still-open or queued rows.
        self.assertNotIn("fifth task", result["archived_text"])
        self.assertNotIn("sixth task", result["archived_text"])

    def test_remainder_still_contains_the_preamble_and_the_open_rows(self):
        result = ra.archive_text(FIXTURE, up_to_task_num=6)
        self.assertIn("Some preamble text", result["remainder_text"])
        self.assertIn("fifth task", result["remainder_text"])
        self.assertIn("sixth task", result["remainder_text"])
        self.assertNotIn("first task", result["remainder_text"])

    def test_remainder_carries_a_pointer_note_naming_the_archived_range(self):
        result = ra.archive_text(FIXTURE, up_to_task_num=6)
        self.assertIn("## Archived: tasks 1-4", result["remainder_text"])

    def test_task_range_and_section_count(self):
        result = ra.archive_text(FIXTURE, up_to_task_num=6)
        self.assertEqual(result["task_range"], (1, 4))
        self.assertEqual(result["sections_archived"], 2)  # the big backlog + task 4's

    def test_nothing_archivable_is_a_clean_no_op_not_an_error(self):
        result = ra.archive_text(FIXTURE, up_to_task_num=0)
        self.assertEqual(result["archived_text"], "")
        self.assertEqual(result["remainder_text"], FIXTURE)
        self.assertIsNone(result["task_range"])


class ArchiveFileContentCase(unittest.TestCase):
    def test_header_prefix_can_be_stripped_to_recover_the_exact_archived_bytes(self):
        result = ra.archive_text(FIXTURE, up_to_task_num=6)
        header, full = ra.build_archive_file_content(
            result["archived_text"], result["task_range"], "ROADMAP.md", "2026-07-20T05:00:00Z"
        )
        self.assertTrue(full.startswith(header))
        self.assertEqual(full[len(header):], result["archived_text"])

    def test_header_names_the_task_range_and_provenance(self):
        result = ra.archive_text(FIXTURE, up_to_task_num=6)
        header, _ = ra.build_archive_file_content(
            result["archived_text"], result["task_range"], "ROADMAP.md", "2026-07-20T05:00:00Z"
        )
        self.assertIn("tasks 1-4", header)
        self.assertIn("roadmap_archive.py", header)
        self.assertIn("task 169", header)


class OnDiskArchiveCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.src = os.path.join(self.tmpdir, "ROADMAP.md")
        with open(self.src, "w", encoding="utf-8") as f:
            f.write(FIXTURE)
        self.out = os.path.join(self.tmpdir, "ROADMAP-ARCHIVE-001-004.md")

    def test_archive_writes_both_files_and_round_trips_through_disk(self):
        result = ra.archive(self.src, up_to_task_num=6, out_path=self.out)
        self.assertEqual(result["task_range"], (1, 4))
        self.assertTrue(os.path.exists(self.out))

        with open(self.out, encoding="utf-8") as f:
            archive_content = f.read()
        with open(self.src, encoding="utf-8") as f:
            remainder_on_disk = f.read()

        self.assertEqual(remainder_on_disk, result["remainder_text"])
        # Recover the archived span from the on-disk archive file (strip
        # the known header) and prove archive+remainder reconstructs the
        # ORIGINAL fixture exactly -- the real round trip, through real
        # files, not just in-memory strings.
        header_end = archive_content.index("---\n\n") + len("---\n\n")
        archived_on_disk = archive_content[header_end:]
        start = FIXTURE.index("## Backlog")
        end = start + len(archived_on_disk)
        reconstructed = FIXTURE[:start] + archived_on_disk + FIXTURE[end:]
        self.assertEqual(reconstructed, FIXTURE)

    def test_refuses_to_overwrite_an_existing_archive_file(self):
        with open(self.out, "w", encoding="utf-8") as f:
            f.write("pre-existing, do not clobber")
        with self.assertRaises(ra.RoadmapArchiveError):
            ra.archive(self.src, up_to_task_num=6, out_path=self.out)
        # And the source file must be untouched by the refused attempt.
        with open(self.src, encoding="utf-8") as f:
            self.assertEqual(f.read(), FIXTURE)

    def test_raises_named_error_when_nothing_is_archivable(self):
        with self.assertRaises(ra.RoadmapArchiveError):
            ra.archive(self.src, up_to_task_num=0, out_path=self.out)
        self.assertFalse(os.path.exists(self.out))


class CLICase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.src = os.path.join(self.tmpdir, "ROADMAP.md")
        with open(self.src, "w", encoding="utf-8") as f:
            f.write(FIXTURE)
        self.script = os.path.join(ROOT, "tools", "roadmap_archive.py")

    def test_plan_subcommand_is_read_only_and_reports_the_range(self):
        with open(self.src, encoding="utf-8") as f:
            before = f.read()
        out = subprocess.run(
            [sys.executable, self.script, "plan", self.src, "--up-to", "6"],
            capture_output=True, text=True, check=True,
        )
        self.assertIn("tasks 1-4", out.stdout)
        with open(self.src, encoding="utf-8") as f:
            after = f.read()
        self.assertEqual(before, after)  # plan never writes

    def test_archive_subcommand_end_to_end(self):
        out_path = os.path.join(self.tmpdir, "ARCHIVE.md")
        result = subprocess.run(
            [sys.executable, self.script, "archive", self.src, "--up-to", "6", "--out", out_path],
            capture_output=True, text=True, check=True,
        )
        self.assertIn("tasks 1-4", result.stdout)
        self.assertTrue(os.path.exists(out_path))

    def test_archive_subcommand_exits_nonzero_and_prints_reason_when_nothing_eligible(self):
        out_path = os.path.join(self.tmpdir, "ARCHIVE.md")
        result = subprocess.run(
            [sys.executable, self.script, "archive", self.src, "--up-to", "0", "--out", out_path],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refused", result.stderr)
        self.assertFalse(os.path.exists(out_path))


class RealRoadmapLiveReadOnlyCase(unittest.TestCase):
    """Proves the parser holds against the REAL, live ROADMAP.md -- read
    only, nothing is ever written back to the real repo by this test.

    Task 170 ran the scalpel task 169 only forged: tasks 1-169 now live,
    byte-for-byte, in the dated archive file this class also reads --
    ROADMAP.md itself is deliberately thin from here on (a preamble, an
    archive pointer, and whatever is currently live). The archive-header
    wrapper (`build_archive_file_content`'s fixed `---\\n\\n` marker) is
    stripped the same way a caller reconstructing the original would.
    """

    def setUp(self):
        self.real_path = os.path.join(ROOT, "ROADMAP.md")
        with open(self.real_path, encoding="utf-8") as f:
            self.real_text = f.read()
        self.archive_path = os.path.join(ROOT, "ROADMAP-ARCHIVE-001-169.md")
        with open(self.archive_path, encoding="utf-8") as f:
            archive_content = f.read()
        marker = "---\n\n"
        self.archived_text = archive_content[archive_content.index(marker) + len(marker):]

    def test_sections_reconstruct_the_real_file_exactly(self):
        sections = ra.split_sections(self.real_text)
        self.assertEqual("".join(s["text"] for s in sections), self.real_text)
        for a, b in zip(sections, sections[1:]):
            self.assertEqual(a["end"], b["start"])

    def test_finds_every_real_task_number_exactly_once_one_through_at_least_168(self):
        # Tasks 1-169's rows now live in the archive file, not the live
        # ROADMAP.md -- that migration is the entire point of task 170.
        sections = ra.split_sections(self.archived_text)
        all_rows = [row for sec in sections for row in ra.section_task_rows(sec["text"])]
        nums = [n for n, _ in all_rows]
        self.assertEqual(len(nums), len(set(nums)), "a task number was parsed twice")
        found = set(nums)
        expected = set(range(1, 169))
        missing = expected - found
        self.assertEqual(missing, set(), f"archive file is missing rows: {sorted(missing)}")

    def test_a_real_sentence_shaped_status_cell_task_19_is_recognized_as_done(self):
        sections = ra.split_sections(self.archived_text)
        all_rows = [row for sec in sections for row in ra.section_task_rows(sec["text"])]
        by_num = dict(all_rows)
        self.assertIn(19, by_num)
        self.assertTrue(by_num[19].upper().startswith("DONE-MACHINERY"))
        self.assertTrue(ra.is_done_status(by_num[19]))

    def test_a_contiguous_prefix_up_to_task_100_is_selectable_and_round_trips(self):
        result = ra.archive_text(self.archived_text, up_to_task_num=100)
        self.assertIsNotNone(result["task_range"])
        lo, hi = result["task_range"]
        self.assertEqual(lo, 1)
        self.assertLessEqual(hi, 100)
        # The real round trip: the exact span this would cut out of the
        # archived text, spliced back, reconstructs the archived text
        # exactly.
        start = self.archived_text.index(result["archived_text"][:200])
        end = start + len(result["archived_text"])
        reconstructed = (
            self.archived_text[:start] + result["archived_text"] + self.archived_text[end:]
        )
        self.assertEqual(reconstructed, self.archived_text)

    def test_wip_rows_are_never_swept_by_an_archive_up_to_their_own_ceiling(self):
        # A cheap, real guard against the "archiving deletes something a
        # doctrine test still needs" risk the task description names:
        # every WIP-reclaim/ritual-completeness check reads ROADMAP.md
        # for OPEN work (WIP rows, the table header), never for closed
        # task prose -- so archiving only ever fully-DONE, sub-ceiling
        # sections can never remove a row those checkers still need.
        # Structural, not a snapshot: today's real file has task 170 WIP
        # (matching `ritual_check.py`'s own `wip_reclaim` fold), and this
        # proves that even a ceiling AT OR ABOVE 170 would still refuse
        # to sweep it up, because its section never reads fully-done.
        sections = ra.split_sections(self.real_text)
        all_rows = [row for sec in sections for row in ra.section_task_rows(sec["text"])]
        wip_rows = [n for n, status in all_rows if not ra.is_done_status(status)]
        if not wip_rows:
            return
        highest_wip = max(wip_rows)
        result = ra.archive_text(self.real_text, up_to_task_num=highest_wip)
        if result["task_range"] is None:
            return
        _, hi = result["task_range"]
        self.assertLess(hi, highest_wip)


if __name__ == "__main__":
    unittest.main()
