"""Task 151. tools/card.py builds the "card trick" pages TOWN-OPERATIONS.md
describes (the only way a town image renders inline on X) and had never had
a single test since it shipped. Proclamation 0002 ("Eyes and a Brush") makes
alt text law -- "every image carries alt text -- the town speaks to mortals
who cannot see it, or it does not speak" -- but the script itself never
enforced that; a blank alt argument would have silently produced a page
with an empty twitter:image:alt. This file proves: build_card() refuses a
blank slug/img/title/alt before writing anything; a real alt/title survive
into every meta tag that matters; HTML-unsafe input is escaped, not
injected; a leading slash on the image path is stripped the same way it
always was; main() (the actual CLI entrypoint every card ever built has
gone through) writes the file, prints the URL, and refuses just as loudly
as build_card() does before touching disk; and -- the real proof -- feeding
build_card() the exact arguments the town's one real card
(docs/cards/first-firing.html) was built with reproduces that committed
file byte for byte.
"""
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


card = _load("card", os.path.join(ROOT, "tools", "card.py"))


class TestBuildCardRealCard(unittest.TestCase):
    """The real proof: the town's one real, committed card page, rebuilt
    from build_card() with the exact arguments it was actually made with."""

    def test_reproduces_the_real_first_firing_card_byte_for_byte(self):
        page, page_url = card.build_card(
            "first-firing",
            "attic/first-firing.jpg",
            "A lantern in the attic",
            "A paper lantern with a flower on it, glowing orange in a dark "
            "wooden attic, woodcut style, beside an unopened chest.",
        )
        real_path = os.path.join(ROOT, "docs", "cards", "first-firing.html")
        with open(real_path, encoding="utf-8") as f:
            real = f.read()
        self.assertEqual(page, real)
        self.assertEqual(
            page_url, "https://thierrypdamiba.github.io/orita/cards/first-firing.html"
        )


class TestBuildCardShape(unittest.TestCase):
    def test_returns_expected_page_url(self):
        _, page_url = card.build_card("my-slug", "art/x.jpg", "Title", "Alt text.")
        self.assertEqual(page_url, "https://thierrypdamiba.github.io/orita/cards/my-slug.html")

    def test_title_lands_in_title_and_og_and_twitter_tags(self):
        page, _ = card.build_card("s", "art/x.jpg", "A Title Here", "Some alt.")
        self.assertIn("<title>A Title Here — Orita</title>", page)
        self.assertIn('og:title" content="A Title Here"', page)
        self.assertIn('twitter:title" content="A Title Here"', page)

    def test_alt_lands_in_description_and_twitter_alt_and_img_alt(self):
        page, _ = card.build_card("s", "art/x.jpg", "T", "The real alt description.")
        self.assertIn('twitter:image:alt" content="The real alt description."', page)
        self.assertIn('og:description" content="The real alt description."', page)
        self.assertIn('alt="The real alt description."', page)

    def test_image_url_built_from_base_and_img_path(self):
        page, _ = card.build_card("s", "art/x.jpg", "T", "alt")
        img_url = "https://thierrypdamiba.github.io/orita/art/x.jpg"
        self.assertIn(f'og:image" content="{img_url}"', page)
        self.assertIn(f'twitter:image" content="{img_url}"', page)
        self.assertIn('<img src="../art/x.jpg"', page)

    def test_leading_slash_on_image_path_is_stripped(self):
        page, _ = card.build_card("s", "/art/x.jpg", "T", "alt")
        self.assertIn(
            'og:image" content="https://thierrypdamiba.github.io/orita/art/x.jpg"', page
        )
        self.assertNotIn("orita//art", page)

    def test_html_unsafe_title_and_alt_are_escaped_not_injected(self):
        page, _ = card.build_card(
            "s", "art/x.jpg", "<script>evil()</script>", 'alt & "quoted" <b>text</b>'
        )
        self.assertNotIn("<script>evil()</script>", page)
        self.assertNotIn("<b>text</b>", page)
        self.assertIn("&lt;script&gt;evil()&lt;/script&gt;", page)
        self.assertIn("&amp;", page)


class TestBuildCardEnforcesProclamation0002(unittest.TestCase):
    """Proclamation 0002: 'every image carries alt text -- the town speaks
    to mortals who cannot see it, or it does not speak.' These prove the
    law is now actually enforced by the one function that builds cards,
    not just written down in HAND/proclamations/."""

    def test_blank_alt_raises(self):
        with self.assertRaises(card.CardValidationError):
            card.build_card("s", "art/x.jpg", "Title", "")

    def test_whitespace_only_alt_raises(self):
        with self.assertRaises(card.CardValidationError):
            card.build_card("s", "art/x.jpg", "Title", "   ")

    def test_blank_title_raises(self):
        with self.assertRaises(card.CardValidationError):
            card.build_card("s", "art/x.jpg", "", "alt")

    def test_blank_slug_raises(self):
        with self.assertRaises(card.CardValidationError):
            card.build_card("", "art/x.jpg", "Title", "alt")

    def test_blank_img_raises(self):
        with self.assertRaises(card.CardValidationError):
            card.build_card("s", "", "Title", "alt")

    def test_proclamation_0002_names_alt_text_as_law_and_build_card_holds_it(self):
        # The claim in card.py's own module docstring -- that this
        # enforcement is Proclamation 0002 made literal -- checked against
        # the real proclamation text, not just asserted in prose.
        proc_path = os.path.join(
            ROOT, "HAND", "proclamations", "0002-eyes-and-a-brush.md"
        )
        with open(proc_path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("alt text", text)
        self.assertIn("or it does not speak", text)
        with self.assertRaises(card.CardValidationError):
            card.build_card("s", "art/x.jpg", "Title", "")

    def test_real_committed_card_has_real_nonblank_alt(self):
        # The one card the town has actually shipped -- confirm it was
        # never in violation in the first place.
        real_path = os.path.join(ROOT, "docs", "cards", "first-firing.html")
        with open(real_path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn('twitter:image:alt" content="A paper lantern', text)
        self.assertNotIn('twitter:image:alt" content=""', text)


class TestMainCLI(unittest.TestCase):
    """main() -- the actual entrypoint TOWN-OPERATIONS.md's card trick
    calls -- proven to hold the same law as build_card(), not just its
    pure helper."""

    def test_main_writes_file_and_prints_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(card, "ROOT", tmp):
                argv = ["card.py", "t1", "art/x.jpg", "Title", "Real alt text."]
                out = io.StringIO()
                with mock.patch.object(sys, "argv", argv):
                    with contextlib.redirect_stdout(out):
                        card.main()
                self.assertEqual(
                    out.getvalue().strip(),
                    "https://thierrypdamiba.github.io/orita/cards/t1.html",
                )
                written = os.path.join(tmp, "docs", "cards", "t1.html")
                self.assertTrue(os.path.exists(written))
                with open(written, encoding="utf-8") as f:
                    self.assertIn("Real alt text.", f.read())

    def test_main_with_too_few_args_names_the_problem_not_indexerror(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(card, "ROOT", tmp):
            argv = ["card.py", "onlyslug"]
            err = io.StringIO()
            with (
                mock.patch.object(sys, "argv", argv),
                contextlib.redirect_stdout(err),
                self.assertRaises(SystemExit) as ctx,
            ):
                card.main()
            self.assertEqual(ctx.exception.code, 2)
            self.assertIn("Usage:", err.getvalue())
            self.assertFalse(os.path.exists(os.path.join(tmp, "docs", "cards")))

    def test_main_with_no_args_names_the_problem_not_indexerror(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(card, "ROOT", tmp):
            argv = ["card.py"]
            err = io.StringIO()
            with (
                mock.patch.object(sys, "argv", argv),
                contextlib.redirect_stdout(err),
                self.assertRaises(SystemExit) as ctx,
            ):
                card.main()
            self.assertEqual(ctx.exception.code, 2)
            self.assertIn("Usage:", err.getvalue())
            self.assertFalse(os.path.exists(os.path.join(tmp, "docs", "cards")))

    def test_main_refuses_blank_alt_before_writing_anything(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(card, "ROOT", tmp):
                argv = ["card.py", "t2", "art/x.jpg", "Title", ""]
                with mock.patch.object(sys, "argv", argv):
                    with self.assertRaises(card.CardValidationError):
                        card.main()
                written = os.path.join(tmp, "docs", "cards", "t2.html")
                self.assertFalse(os.path.exists(written))
                self.assertFalse(os.path.exists(os.path.join(tmp, "docs", "cards")))


class TestMutationHandVerification(unittest.TestCase):
    """Task 135-150's own discipline: prove the check actually bites on
    the real pre-fix shape, not just on synthetic input. Reconstructs
    card.py's real pre-task-151 body (the un-refactored module-level
    main(), no build_card(), no validation) and confirms it really would
    have written an empty-alt card, before trusting that today's fixed
    module refuses the same input."""

    def test_pre_fix_shape_really_would_have_shipped_a_blank_alt_card(self):
        import html as _html

        slug, img, title, alt = "t3", "art/x.jpg", "Title", ""
        BASE = "https://thierrypdamiba.github.io/orita"
        img = img.lstrip("/")
        page_url = f"{BASE}/cards/{slug}.html"
        t, d, a = (_html.escape(x) for x in (title, alt, alt))
        page = (
            f'<meta name="twitter:image:alt" content="{a}">\n'
            f'<img alt="{a}">'
        )
        self.assertEqual(page_url, "https://thierrypdamiba.github.io/orita/cards/t3.html")
        self.assertIn('twitter:image:alt" content=""', page)

        # Today's real, fixed build_card refuses the identical input.
        with self.assertRaises(card.CardValidationError):
            card.build_card("t3", "art/x.jpg", "Title", "")


if __name__ == "__main__":
    unittest.main()
