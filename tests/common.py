"""Shared helpers for the checks in this directory.

check_build.py asserts on a local build; check_live.py asserts on a deployed site.
They ask overlapping questions (is this llms.txt well formed, does this JSON-LD name a
Person, is the 404 body small), so the parsing and the constants behind those questions
live here rather than in both files, where they had already drifted apart.

Both scripts are run by path, so `tests/` is on sys.path and `import common` works with
no packaging. Standard library only, deliberately: these run anywhere Hugo does.
"""

import json
import re
from html.parser import HTMLParser

# The site emits absolute URLs by design (correct for canonical/OG), so the production
# origin is a real guarantee worth pinning rather than deriving from the build.
BASE_URL = "https://chrispanag.com"

# The machine-readable surface an agent is pointed at, and the media type each one
# serves. layouts/404.html and layouts/home.llms.txt link these; home.openapi.json
# documents them. Keep in step with those templates when adding an endpoint.
INDEX_FILES = {
    "/llms.txt": "text/plain",
    "/robots.txt": "text/plain",
    "/sitemap.xml": "xml",
    "/index.xml": "xml",
    "/index.json": "json",
    "/openapi.json": "json",
}

# What a 404 body must link to so an agent can recover. A subset of INDEX_FILES:
# robots.txt is a crawl policy, not a route to content, so the 404 page omits it.
RECOVERY_TARGETS = ("/llms.txt", "/sitemap.xml", "/index.json", "/index.xml",
                    "/openapi.json")

# A 404 body should be short and link-dense. This guards against someone turning it
# into a full page listing, which is what makes agents give up on recovering.
MAX_404_BYTES = 20_000

# Markdown link entries in an llms.txt file list.
LLMS_LINK_RE = re.compile(r"^- \[[^\]]+\]\(([^)]+)\)", re.MULTILINE)

SKIP_TEXT_TAGS = {"script", "style", "svg", "noscript", "template"}


class Page(HTMLParser):
    """Minimal HTML reader: visible text, links, h1s, and <link>/<meta> tags."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.text_parts = []
        self.links = []
        self.h1s = []
        self.link_tags = []
        self.metas = []
        self.title = ""
        self._skip_depth = 0
        self._in_title = False
        self._h1 = None
        self.feed(html)
        # feed() buffers a trailing run of text when convert_charrefs is on, in case a
        # character reference is still being assembled. close() flushes it, so without
        # this the end of the document can be missing from .text.
        self.close()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in SKIP_TEXT_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._h1 = []
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        elif tag == "link":
            self.link_tags.append(attrs)
        elif tag == "meta":
            self.metas.append(attrs)

    def handle_endtag(self, tag):
        if tag in SKIP_TEXT_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
        elif tag == "h1" and self._h1 is not None:
            self.h1s.append("".join(self._h1).strip())
            self._h1 = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._skip_depth:
            return
        self.text_parts.append(data)
        if self._h1 is not None:
            self._h1.append(data)

    @property
    def text(self):
        return re.sub(r"\s+", " ", "".join(self.text_parts)).strip()

    def meta(self, **match):
        """The content of the first <meta> whose attributes match, or None."""
        for tag in self.metas:
            if all(tag.get(k) == v for k, v in match.items()):
                return tag.get("content")
        return None

    def link(self, rel):
        """The href of the first <link> carrying `rel`, or None."""
        for tag in self.link_tags:
            if rel in (tag.get("rel") or "").split():
                return tag.get("href")
        return None


def json_ld(html):
    """Every application/ld+json block on a page, parsed."""
    blocks = re.findall(
        r'(?is)<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html
    )
    return [json.loads(b) for b in blocks]


def graph_nodes(blocks):
    """The @graph of the first JSON-LD block, keyed by @type. Empty if absent."""
    if not blocks:
        return {}
    return {node.get("@type"): node for node in blocks[0].get("@graph", [])}


def is_alias_stub(html):
    """True for the meta-refresh stubs Hugo writes for aliases.

    pagination.disableAliases is false in config.yml, so /posts/page/1/ and friends are
    two-line redirects rendered without the head partials. Per-post `aliases:` front
    matter produces the same shape. They are redirects, not pages.
    """
    return re.search(r'http-equiv\s*=\s*"?refresh', html) is not None


class Report:
    """Prints each assertion as it runs and tallies the outcome.

    `check` is a hard assertion. `note` is for things this repo cannot make true on its
    own (an edge-only feature, a design decision taken deliberately): they are reported
    as PENDING and kept out of the exit code, so a red run always means a real break.
    """

    # Wide enough for the longest label ("PENDING"), so names line up in a column.
    LABEL_WIDTH = 7

    def __init__(self):
        self.passed = 0
        self.failures = []
        self.pending = []

    def _say(self, label, name, detail=""):
        print(f"  {label:<{self.LABEL_WIDTH}} {name}")
        if detail:
            print(f"  {'':<{self.LABEL_WIDTH}} {detail}")

    def check(self, name, ok, detail=""):
        if ok:
            self.passed += 1
            self._say("ok", name)
        else:
            self.failures.append(name)
            self._say("FAIL", name, detail)

    def equal(self, name, actual, expected):
        self.check(name, actual == expected, f"expected {expected!r}, got {actual!r}")

    def note(self, name, ok, detail):
        if ok:
            self.passed += 1
            self._say("ok", name)
        else:
            self.pending.append(name)
            self._say("PENDING", name, detail)

    def summary(self):
        """Print the tally and return the exit code."""
        tail = f", {len(self.pending)} pending" if self.pending else ""
        print(f"\n{self.passed} passed, {len(self.failures)} failed{tail}")
        for name in self.failures:
            print(f"  FAILED:  {name}")
        for name in self.pending:
            print(f"  PENDING: {name}")
        return 1 if self.failures else 0


def check_llms_shape(report, text, label="llms.txt"):
    """Assert the llmstxt.org v2 preamble: H1, then a blockquote summary.

    Returns the link targets found in the file lists.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    report.check(f"{label} starts with an H1",
                 bool(lines) and lines[0].startswith("# "),
                 f"got {lines[0]!r}" if lines else "file is empty")
    report.check(f"{label} follows the H1 with a blockquote summary",
                 len(lines) > 1 and lines[1].startswith("> "),
                 f"got {lines[1]!r}" if len(lines) > 1 else "no second line")
    return LLMS_LINK_RE.findall(text)


def check_person_node(report, person, label="Person"):
    """Assert the shape of the home page's schema.org Person node."""
    # The bug the schema fork exists to fix: the theme pointed image at favicon.ico.
    image = person.get("image", "")
    report.check(f"{label}.image is the profile photo, not the favicon",
                 bool(image) and "favicon" not in image, f"got {image!r}")
    for field in ("name", "url", "description", "jobTitle", "worksFor", "sameAs"):
        report.check(f"{label}.{field} is set", bool(person.get(field)))
    report.check(f"{label}.sameAs are all absolute https URLs",
                 all(str(u).startswith("https://") for u in person.get("sameAs", [])),
                 f"got {person.get('sameAs')!r}")
