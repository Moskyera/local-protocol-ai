"""The startup update check.

It runs on every boot, so the properties that matter are not features:
it must never block, never lie, and never shout when there is nothing to say.
"""

import json
import os
import sys
import tempfile
import urllib.error

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_ai import updater as U  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Never touch the real cache, and never carry state between tests."""
    monkeypatch.setattr(U, "CACHE_FILE", tmp_path / "cache.json")
    yield


def _release(tag, body="", published="2026-01-01T00:00:00Z", **kw):
    d = {"tag_name": tag, "body": body, "published_at": published,
         "html_url": f"https://example.invalid/{tag}", "draft": False,
         "prerelease": False}
    d.update(kw)
    return d


def _feed(monkeypatch, releases):
    monkeypatch.setattr(U, "_fetch", lambda url: releases)


class TestItNeverLies:
    """The failure the whole project has been removing: reporting success when
    nothing happened. 'Up to date' must mean 'I asked and the answer was no',
    never 'I could not ask'."""

    def test_an_unreachable_feed_reports_that_it_could_not_check(self, monkeypatch):
        def dead(url):
            raise OSError("network is unreachable")

        monkeypatch.setattr(U, "_fetch", dead)
        u = U.check("o/r", "1.0.0", force=True)
        assert u is not None and u.error
        assert u.available is False

    def test_the_banner_says_so_in_words(self, monkeypatch):
        monkeypatch.setattr(U, "_fetch", lambda url: (_ for _ in ()).throw(OSError("x")))
        out = U.render(U.check("o/r", "1.0.0", force=True))
        assert "Could not check" in out
        assert "NOT a statement that you are" in out

    def test_a_404_is_not_treated_as_up_to_date(self, monkeypatch):
        def missing(url):
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, None)

        monkeypatch.setattr(U, "_fetch", missing)
        u = U.check("o/nope", "1.0.0", force=True)
        assert u.error == "HTTP 404"

    def test_an_unparseable_version_never_claims_an_update(self, monkeypatch):
        """Guessing here would put a false banner in front of every boot."""
        _feed(monkeypatch, [_release("nightly-build")])
        assert U.check("o/r", "1.0.0", force=True) is None


class TestItSaysNothingWhenThereIsNothingToSay:
    def test_current_version_prints_nothing(self, monkeypatch):
        _feed(monkeypatch, [_release("v1.0.0")])
        assert U.check("o/r", "1.0.0", force=True) is None
        assert U.render(None) == ""

    def test_a_newer_local_version_is_not_a_downgrade_prompt(self, monkeypatch):
        _feed(monkeypatch, [_release("v1.0.0")])
        assert U.check("o/r", "2.0.0", force=True) is None

    def test_an_empty_feed_is_silent(self, monkeypatch):
        _feed(monkeypatch, [])
        assert U.check("o/r", "1.0.0", force=True) is None

    def test_drafts_and_prereleases_are_ignored(self, monkeypatch):
        _feed(monkeypatch, [_release("v9.0.0", draft=True),
                            _release("v8.0.0", prerelease=True),
                            _release("v1.0.0")])
        assert U.check("o/r", "1.0.0", force=True) is None


class TestItShowsWhatChanged:
    FEED = [
        _release("v1.3.0", "- feat: third thing\n- fix: a bug", "2026-03-01T00:00:00Z"),
        _release("v1.2.0", "- feat: second thing", "2026-02-01T00:00:00Z"),
        _release("v1.1.0", "- feat: first thing", "2026-01-01T00:00:00Z"),
        _release("v1.0.0", "- initial", "2025-12-01T00:00:00Z"),
    ]

    def test_it_reports_the_newest(self, monkeypatch):
        _feed(monkeypatch, self.FEED)
        u = U.check("o/r", "1.0.0", force=True)
        assert u.latest == "1.3.0"
        assert u.available is True

    def test_every_skipped_release_is_listed(self, monkeypatch):
        """Someone three releases behind should see all three, not only the last."""
        _feed(monkeypatch, self.FEED)
        u = U.check("o/r", "1.0.0", force=True)
        assert [r["version"] for r in u.releases] == ["1.3.0", "1.2.0", "1.1.0"]

    def test_the_running_version_is_not_listed_as_new(self, monkeypatch):
        _feed(monkeypatch, self.FEED)
        u = U.check("o/r", "1.2.0", force=True)
        assert [r["version"] for r in u.releases] == ["1.3.0"]

    def test_the_notes_reach_the_banner(self, monkeypatch):
        _feed(monkeypatch, self.FEED)
        out = U.render(U.check("o/r", "1.0.0", force=True))
        assert "third thing" in out and "first thing" in out


class TestTheBannerIsWellFormed:
    def test_generated_html_comments_are_stripped(self):
        """GitHub's generated bodies open with a comment naming the config file
        that produced them. It was the first line shown in the banner."""
        body = ("<!-- Release notes generated using configuration in "
                ".github/release.yml at main -->\n- feat: a real change")
        pts = U._bullets(body)
        assert pts and not any("release.yml" in p for p in pts)
        assert any("a real change" in p for p in pts)

    def test_headings_and_contributor_lists_are_dropped(self):
        body = "## What's Changed\n- feat: x\n## New Contributors\n- @someone"
        pts = U._bullets(body)
        assert any("feat: x" in p for p in pts)
        assert not any("@someone" in p for p in pts)

    @pytest.mark.parametrize("ch,cols", [
        ("a", 1),
        ("─", 1),               # box drawing rule
        ("…", 1),               # ellipsis
        ("🆕", 2),           # emoji presentation by default
        ("⚠", 1),               # WARNING SIGN alone is NARROW...
        ("⚠️", 2),         # ...and wide only with the selector
    ])
    def test_display_width_matches_what_a_terminal_draws(self, ch, cols):
        """Grounded, not self-referential.

        The first version of this test only asserted every line had the same
        _dw, which _dw satisfied while being wrong: it counted the whole
        0x2600-0x27BF block as double-width, so the line carrying the warning
        sign rendered one column short of the others on screen.
        """
        assert U._dw(ch) == cols

    def test_every_line_is_the_same_display_width(self, monkeypatch):
        _feed(monkeypatch, [_release("v2.0.0", "- feat: something")])
        out = U.render(U.check("o/r", "1.0.0", force=True))
        widths = {U._dw(line) for line in out.splitlines()}
        assert len(widths) == 1, sorted(widths)

    def test_the_error_banner_is_also_square(self, monkeypatch):
        monkeypatch.setattr(U, "_fetch", lambda url: (_ for _ in ()).throw(OSError("x")))
        out = U.render(U.check("o/r", "1.0.0", force=True))
        widths = {U._dw(line) for line in out.splitlines()}
        assert len(widths) == 1, sorted(widths)


class TestItDoesNotSlowTheBoot:
    def test_a_successful_check_is_cached(self, monkeypatch):
        calls = []

        def counting(url):
            calls.append(url)
            return [_release("v1.0.0")]

        monkeypatch.setattr(U, "_fetch", counting)
        U.check("o/r", "1.0.0", force=True)
        U.check("o/r", "1.0.0")
        U.check("o/r", "1.0.0")
        assert len(calls) == 1, "the launcher must not hit GitHub on every run"

    def test_the_timeout_is_bounded(self):
        assert 0 < U.TIMEOUT <= 10, "an unbounded check would hang the boot"

    def test_a_broken_cache_file_does_not_raise(self, monkeypatch, tmp_path):
        U.CACHE_FILE.write_text("{ not json", encoding="utf-8")
        _feed(monkeypatch, [_release("v1.0.0")])
        assert U.check("o/r", "1.0.0") is None


class TestVersionParsing:
    @pytest.mark.parametrize("a,b,expected", [
        ("1.2.0", "1.1.9", True),
        ("1.10.0", "1.9.0", True),          # not string comparison
        ("1.0.0", "1.0.0", False),
        ("1.0.0", "1.0.1", False),
        ("v2.0.0", "1.9.9", True),          # a leading v is tolerated
        ("2.0.0-rc1", "1.0.0", True),
        ("garbage", "1.0.0", False),
        ("1.0.0", "garbage", False),
        ("", "1.0.0", False),
    ])
    def test_comparison(self, a, b, expected):
        assert U._newer(a, b) is expected

    def test_a_missing_version_file_does_not_raise(self, monkeypatch, tmp_path):
        monkeypatch.setattr(U, "VERSION_FILE", tmp_path / "nope")
        assert U.current_version() == "0.0.0"


class TestStartupEntryPoint:
    """`python -m local_ai`, run by the launcher before anything heavy."""

    def test_an_unconfigured_repo_checks_nothing_and_says_nothing(self, monkeypatch):
        """Before the project is published there is no repo to ask about.

        Inventing a name and then warning that the invention 404s puts a
        warning box in front of every boot about a problem that is entirely
        of our own making.
        """
        called = []
        monkeypatch.setattr(U, "_fetch", lambda url: called.append(url) or [])
        assert U.check("", "1.0.0", force=True) is None
        assert called == []

    def test_repo_comes_from_the_git_remote(self, monkeypatch, tmp_path):
        """A plain `git clone` must be configured correctly with no setup."""
        monkeypatch.delenv("LOCAL_AI_REPO", raising=False)
        import subprocess as sp

        class R:
            stdout = "https://github.com/someone/local-ai.git" + chr(10)

        monkeypatch.setattr(sp, "run", lambda *a, **k: R())
        assert U.default_repo() == "someone/local-ai"

    def test_an_explicit_env_var_wins(self, monkeypatch):
        monkeypatch.setenv("LOCAL_AI_REPO", "org/mirror")
        assert U.default_repo() == "org/mirror"

    def test_it_always_exits_zero(self, monkeypatch):
        """A failed update check must never be why the stack did not boot."""
        from local_ai import __main__ as M

        monkeypatch.setattr(M.updater, "check",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        assert M.main([]) == 0

    def test_the_ascii_fallback_keeps_the_columns(self, monkeypatch):
        """When output is piped rather than shown in a console, the box
        characters cannot be encoded. The replacement must be the same width
        or the table arrives crooked in the log file."""
        from local_ai import __main__ as M

        _feed(monkeypatch, [_release("v2.0.0", "- feat: something")])
        banner = U.render(U.check("o/r", "1.0.0", force=True))
        plain = M.to_ascii(banner)
        plain.encode("ascii")          # raises if anything was missed
        assert [U._dw(x) for x in plain.splitlines()] ==                [U._dw(x) for x in banner.splitlines()]


class TestReleaseNotesAreCleaned:
    """Real release bodies are markdown, HTML, or both. What reaches a
    terminal banner has to be plain text."""

    def test_a_markdown_link_keeps_its_text_and_loses_its_target(self):
        r"""Order matters. Stripping bare URLs first left the wreckage behind:
        "[#14220](https://...)" rendered as the literal "[\#14220](" ."""
        pts = U._bullets("- [#14220](https://github.com/x/y/issues/14220) Fixed a bug")
        assert pts == ["#14220 Fixed a bug"]

    def test_html_tags_do_not_reach_the_terminal(self):
        pts = U._bullets('- Fixed <span class="title-ref">RaisesGroup</span> handling')
        assert pts == ["Fixed RaisesGroup handling"]

    def test_backslash_escapes_are_undone(self):
        assert U._bullets(r"- Fixed issue \#14220")[0] == "Fixed issue #14220"

    def test_a_very_long_line_is_cut_at_a_word_and_marked(self):
        pts = U._bullets("- " + "word " * 100)
        assert len(pts[0]) <= U.MAX_BULLET + 2
        assert pts[0].endswith("…")

    def test_bullets_are_uncapped_so_the_caller_can_count_what_it_drops(self):
        body = "\n".join(f"- change number {i}" for i in range(20))
        assert len(U._bullets(body)) == 20

    def test_the_banner_states_how_many_changes_it_did_not_show(self, monkeypatch):
        """A banner showing 3 of 20 changes without saying so reads as
        'that is all of them'."""
        body = "\n".join(f"- change number {i}" for i in range(20))
        _feed(monkeypatch, [_release("v2.0.0", body)])
        out = U.render(U.check("o/r", "1.0.0", force=True))
        assert f"{20 - U.MAX_BULLETS} more change(s)" in out

    def test_the_banner_states_how_many_releases_it_did_not_show(self, monkeypatch):
        feed = [_release(f"v1.{i}.0", "- a change") for i in range(9, 0, -1)]
        _feed(monkeypatch, feed)
        out = U.render(U.check("o/r", "1.0.0", force=True))
        assert f"{9 - U.MAX_RELEASES} earlier release(s) not shown" in out

    def test_the_banner_stays_short_enough_to_read_at_boot(self, monkeypatch):
        """The first version rendered 80 lines from a real feed."""
        body = "\n".join(f"- {'word ' * 60}" for _ in range(30))
        _feed(monkeypatch, [_release(f"v9.{i}.0", body) for i in range(9, 0, -1)])
        out = U.render(U.check("o/r", "1.0.0", force=True))
        assert len(out.splitlines()) <= 40, len(out.splitlines())
