#!/usr/bin/env python3
"""Assertions over a built Hugo site (the ./public tree).

Run through tests/run.sh, which does the build first. These cover the agent-readiness
behavior added in layouts/home.html, layouts/404.html, layouts/llms.txt and
layouts/home.openapi.json, plus regression guards on the outputs those changes touch
(search index, sitemap, feed, home page metadata).

Only the standard library is used, so this runs anywhere Hugo does.
"""

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

BASE_URL = "https://chrispanag.com"

# Kept in sync with params.description in config.yml. The home page must keep serving
# this as its meta/og/twitter description even though content/_index.md now has a body.
SITE_DESCRIPTION = (
    "Engineering Manager at Prelude (ex-BeReal). I build backend and platform "
    "systems at scale, and the teams behind them."
)

SITE_TITLE = "Christos Panagiotakopoulos"

# A 404 body should be short and link-dense. This guards against someone turning it
# into a full page listing, which is what makes agents give up on recovering.
MAX_404_BYTES = 20_000

SKIP_TEXT_TAGS = {"script", "style", "svg", "noscript", "template"}


class Page(HTMLParser):
    """Minimal HTML reader: visible text, links, headings, and <link>/<meta> tags."""

    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.text_parts = []
        self.links = []
        self.headings = {}
        self.link_tags = []
        self.metas = []
        self.title = ""
        self._skip_depth = 0
        self._stack = []
        self._capture = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in SKIP_TEXT_TAGS:
            self._skip_depth += 1
        self._stack.append(tag)
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        elif tag == "link":
            self.link_tags.append(attrs)
        elif tag == "meta":
            self.metas.append(attrs)
        elif re.fullmatch(r"h[1-6]", tag):
            self._capture = (tag, [])

    def handle_endtag(self, tag):
        if tag in SKIP_TEXT_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if self._stack and tag in self._stack:
            while self._stack.pop() != tag:
                pass
        if self._capture and self._capture[0] == tag:
            level, parts = self._capture
            self.headings.setdefault(level, []).append("".join(parts).strip())
            self._capture = None

    def handle_data(self, data):
        if self._stack and self._stack[-1] == "title":
            self.title += data
        if self._skip_depth:
            return
        self.text_parts.append(data)
        if self._capture:
            self._capture[1].append(data)

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
        for tag in self.link_tags:
            if tag.get("rel") == rel or rel in (tag.get("rel") or "").split():
                return tag.get("href")
        return None


class Results:
    def __init__(self):
        self.passed = 0
        self.failures = []

    def check(self, name, ok, detail=""):
        if ok:
            self.passed += 1
            print(f"  ok   {name}")
        else:
            self.failures.append((name, detail))
            print(f"  FAIL {name}" + (f"\n         {detail}" if detail else ""))

    def equal(self, name, actual, expected):
        self.check(name, actual == expected, f"expected {expected!r}, got {actual!r}")


def local_path(out: Path, url: str):
    """Map a site URL onto the file the build actually wrote, or None.

    "/about" and "/about/" both resolve: menu.main in config.yml spells section URLs
    without the trailing slash, and the host serves them from about/index.html.
    """
    path = urlsplit(url).path.lstrip("/")
    for candidate in (out / path, out / path / "index.html"):
        if candidate.is_file():
            return candidate
    return None


def is_alias_stub(html: str) -> bool:
    """True for the meta-refresh stubs Hugo writes for pagination aliases.

    pagination.disableAliases is false in config.yml, so /posts/page/1/ and friends are
    two-line redirects rendered without the head partials. They are not pages.
    """
    return "http-equiv=refresh" in html.replace('"', "").replace(" =", "=")


def check_home(out: Path, r: Results):
    print("\nhome page (PaperMod profile card, deliberately minimal)")
    html = (out / "index.html").read_text(encoding="utf-8")
    page = Page(html)

    h1s = page.headings.get("h1", [])
    r.equal("exactly one h1", len(h1s), 1)
    r.check("h1 is the site name", h1s[:1] == [SITE_TITLE], f"got {h1s!r}")

    r.check("profile subtitle rendered", "Engineering Manager @ Prelude" in page.text)
    for label in ("Blog", "About", "On the web"):
        r.check(f"profile button {label!r} rendered", label in page.text)

    # The home page is the profile card and nothing else: no body copy below the hero,
    # none added inside the card either. That is a deliberate design decision, and it
    # outranks the crawler heuristic that wants 500+ characters of text on `/`. There
    # is therefore no assertion on text length; check_live.py reports it as PENDING.
    # Anything that would satisfy that heuristic has to be visible, so it cannot be
    # added without changing the design.
    r.check(
        "nothing renders below the profile card",
        "post-content" not in html,
        "the home page is meant to be the profile card only",
    )
    r.check(
        "no prose added inside the profile card",
        "profile-bio" not in html,
        "the profile card is meant to stay name + subtitle + icons + buttons",
    )

    # The home page takes its title and descriptions from site config. Giving
    # content/_index.md a body would silently override og:/twitter: descriptions, since
    # the theme resolves `or .Description .Summary site.Params.description`.
    r.equal("<title>", page.title, SITE_TITLE)
    r.equal("meta description", page.meta(name="description"), SITE_DESCRIPTION)
    r.equal("og:description", page.meta(property="og:description"), SITE_DESCRIPTION)
    r.equal("twitter:description", page.meta(name="twitter:description"), SITE_DESCRIPTION)


def check_404(out: Path, r: Results):
    print("\n404 page (layouts/404.html)")
    raw = (out / "404.html").read_bytes()
    page = Page(raw.decode("utf-8"))

    r.check(
        f"body stays under {MAX_404_BYTES} bytes",
        len(raw) < MAX_404_BYTES,
        f"got {len(raw)} bytes",
    )
    r.check("has an h1", len(page.headings.get("h1", [])) == 1, f"got {page.headings.get('h1')!r}")

    # The recovery links an agent needs in order to find the real pages.
    for name in ("llms.txt", "sitemap.xml", "index.json", "index.xml", "openapi.json"):
        r.check(f"links to /{name}", f"{BASE_URL}/{name}" in page.links)

    # Every page in the nav, spelled canonically (with the trailing slash).
    for path in ("/", "/about/", "/chrispanag-on-the-web/", "/posts/", "/search/"):
        r.check(f"links to {path}", BASE_URL + path in page.links)

    # Nothing is worse than a recovery page whose own links 404.
    broken = [
        href for href in page.links
        if href.startswith(BASE_URL) and local_path(out, href) is None
    ]
    r.check("every link resolves to a built file", not broken, f"broken: {broken}")


def check_openapi(out: Path, r: Results):
    print("\nopenapi.json (layouts/home.openapi.json)")
    path = out / "openapi.json"
    if not path.is_file():
        r.check("openapi.json exists", False, "file not written")
        return

    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        r.check("openapi.json is valid JSON", False, str(exc))
        return
    r.check("openapi.json is valid JSON", True)

    # It must not be the search index: both are .json on the home page, and an earlier
    # template name made Hugo resolve this output format to layouts/index.json.
    r.check("is an OpenAPI document, not the search index", isinstance(spec, dict))
    if not isinstance(spec, dict):
        return

    r.check("openapi version is 3.1.x", str(spec.get("openapi", "")).startswith("3.1"))
    info = spec.get("info", {})
    for field in ("title", "version", "description"):
        r.check(f"info.{field} is set", bool(info.get(field)))
    r.equal("servers[0].url has no trailing slash", spec.get("servers", [{}])[0].get("url"), BASE_URL)

    paths = spec.get("paths", {})
    r.check("declares paths", bool(paths))
    r.check(
        "every path starts with /",
        all(p.startswith("/") for p in paths),
        f"bad: {[p for p in paths if not p.startswith('/')]}",
    )

    missing_responses = [
        f"{method} {p}"
        for p, item in paths.items()
        for method, op in item.items()
        if not op.get("responses")
    ]
    r.check("every operation declares responses", not missing_responses, f"{missing_responses}")

    ids = [op.get("operationId") for item in paths.values() for op in item.values()]
    r.check("operationIds are unique and present", all(ids) and len(ids) == len(set(ids)), f"{ids}")

    # Every $ref must resolve inside the document.
    refs = re.findall(r'"\$ref"\s*:\s*"([^"]+)"', path.read_text(encoding="utf-8"))
    unresolved = []
    for ref in refs:
        node = spec
        for part in ref.lstrip("#/").split("/"):
            node = node.get(part) if isinstance(node, dict) else None
            if node is None:
                unresolved.append(ref)
                break
    r.check("every $ref resolves", not unresolved, f"unresolved: {unresolved}")

    # The spec describes this site, so each concrete path must be something the build
    # really wrote. Templated paths (/{path}, /posts/{slug}/) are checked separately.
    concrete = [p for p in paths if "{" not in p]
    missing = [p for p in concrete if local_path(out, BASE_URL + p) is None]
    r.check("every concrete path exists in the build", not missing, f"missing: {missing}")

    # The slug enum must match the posts on disk, or agents get 404s from the spec.
    slugs = set()
    for item in paths.get("/posts/{slug}/", {}).values():
        for param in item.get("parameters", []):
            if param.get("name") == "slug":
                slugs = set(param.get("schema", {}).get("enum", []))
    on_disk = {p.parent.name for p in (out / "posts").glob("*/index.html")}
    r.equal("slug enum matches the built posts", slugs, on_disk)

    # The 404 contract this site actually implements has to be in the spec.
    r.check("documents a 404 for unknown paths", "404" in paths.get("/{path}", {}).get("get", {}).get("responses", {}))


def check_llms_txt(out: Path, r: Results):
    print("\nllms.txt (layouts/llms.txt, llmstxt.org v2 format)")
    text = (out / "llms.txt").read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]

    r.check("starts with an H1", lines[0].startswith("# "), f"got {lines[0]!r}")
    r.check("H1 is followed by a blockquote summary", lines[1].startswith("> "), f"got {lines[1]!r}")
    r.check("blockquote carries the site description", SITE_DESCRIPTION in lines[1])

    headings = [ln for ln in lines if ln.startswith("## ")]
    r.check("has H2 file lists", len(headings) >= 2, f"got {headings!r}")
    r.check('has the conventional "## Optional" section', "## Optional" in headings)

    # Every file list entry sits under a heading, and every heading precedes its list.
    seen_heading = False
    orphan_items = []
    for line in lines:
        if line.startswith("## "):
            seen_heading = True
        elif line.startswith("- ") and not seen_heading:
            orphan_items.append(line)
    r.check("no list item appears before its heading", not orphan_items, f"{orphan_items}")

    links = re.findall(r"^- \[[^\]]+\]\(([^)]+)\)", text, re.MULTILINE)
    r.check("has link entries", bool(links))
    r.check(
        "every link is an absolute URL",
        all(link.startswith("https://") for link in links),
        f"relative: {[l for l in links if not l.startswith('https://')]}",
    )
    broken = [link for link in links if local_path(out, link) is None]
    r.check("every link resolves to a built file", not broken, f"broken: {broken}")
    r.check("points at openapi.json", f"{BASE_URL}/openapi.json" in links)


def check_discovery_links(out: Path, r: Results):
    print("\ndiscovery links in <head> (layouts/_partials/extend_head.html)")
    missing_described, missing_service = [], []
    pages = []
    for page_path in sorted(out.glob("**/index.html")):
        html = page_path.read_text(encoding="utf-8")
        if is_alias_stub(html):
            continue
        pages.append(page_path)
        page = Page(html)
        if page.link("describedby") != f"{BASE_URL}/llms.txt":
            missing_described.append(str(page_path.relative_to(out)))
        if page.link("service-desc") != f"{BASE_URL}/openapi.json":
            missing_service.append(str(page_path.relative_to(out)))

    r.check("build produced HTML pages", bool(pages))
    r.check("404 page is not an alias stub", not is_alias_stub((out / "404.html").read_text(encoding="utf-8")))
    r.check("every page links rel=describedby to llms.txt", not missing_described, f"{missing_described[:5]}")
    r.check("every page links rel=service-desc to openapi.json", not missing_service, f"{missing_service[:5]}")


def json_ld(html: str):
    """Every application/ld+json block on a page, parsed."""
    blocks = re.findall(
        r'(?is)<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html
    )
    return [json.loads(b) for b in blocks]


def check_structured_data(out: Path, r: Results):
    print("\nstructured data (layouts/_partials/templates/schema_json.html)")
    html = (out / "index.html").read_text(encoding="utf-8")
    page = Page(html)

    try:
        blocks = json_ld(html)
    except json.JSONDecodeError as exc:
        r.check("home JSON-LD parses", False, str(exc))
        return
    r.check("home JSON-LD parses", True)
    r.equal("home emits exactly one JSON-LD block", len(blocks), 1)
    if not blocks:
        return

    graph = blocks[0].get("@graph", [])
    by_type = {node.get("@type"): node for node in graph}
    r.check("home graph has a ProfilePage", "ProfilePage" in by_type, f"got {list(by_type)}")
    r.check("home graph has a Person", "Person" in by_type, f"got {list(by_type)}")
    if not {"ProfilePage", "Person"} <= set(by_type):
        return

    profile, person = by_type["ProfilePage"], by_type["Person"]
    r.equal(
        "ProfilePage.mainEntity points at the Person",
        profile.get("mainEntity", {}).get("@id"),
        person.get("@id"),
    )

    # The bug this fork exists to fix: the theme pointed Person.image at favicon.ico.
    image = person.get("image", "")
    r.check("Person.image is not the favicon", "favicon" not in image, f"got {image!r}")
    r.equal("Person.image agrees with og:image", image, page.meta(property="og:image"))

    for field in ("name", "url", "description", "jobTitle", "worksFor", "homeLocation",
                  "knowsAbout", "sameAs"):
        r.check(f"Person.{field} is set", bool(person.get(field)))
    r.check(
        "Person.sameAs are all absolute https URLs",
        all(str(u).startswith("https://") for u in person.get("sameAs", [])),
        f"got {person.get('sameAs')!r}",
    )
    r.check(
        "Person.worksFor is an Organization with a url",
        person.get("worksFor", {}).get("@type") == "Organization"
        and person.get("worksFor", {}).get("url", "").startswith("https://"),
        f"got {person.get('worksFor')!r}",
    )

    # The rest of that partial is the theme's code, carried over verbatim by the fork.
    # If a PaperMod bump is re-synced badly, these are what break first.
    post = next(iter(sorted((out / "posts").glob("*/index.html"))), None)
    r.check("a post page exists to check", post is not None)
    if post:
        types = [n.get("@type") for n in json_ld(post.read_text(encoding="utf-8"))]
        r.check("posts still emit BreadcrumbList and BlogPosting",
                {"BreadcrumbList", "BlogPosting"} <= set(types), f"got {types}")
    section_types = [
        n.get("@type") for n in json_ld((out / "posts" / "index.html").read_text(encoding="utf-8"))
    ]
    r.check("sections still emit BreadcrumbList", "BreadcrumbList" in section_types,
            f"got {section_types}")


def check_regressions(out: Path, r: Results):
    print("\nunchanged outputs (regression guards)")

    # Search: config.yml's outputs.home must keep JSON, and the shape Fuse.js indexes.
    index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    r.check("index.json is a non-empty array", isinstance(index, list) and index)
    r.check(
        "index.json entries keep the Fuse.js keys",
        all({"title", "content", "permalink", "summary"} <= set(e) for e in index),
    )
    # The home page is not a RegularPage, so its new body must not leak into search.
    r.check(
        "home page did not enter the search index",
        all(e["permalink"].rstrip("/") != BASE_URL for e in index),
    )

    sitemap = (out / "sitemap.xml").read_text(encoding="utf-8")
    for path in ("/", "/about/", "/posts/"):
        r.check(f"sitemap lists {path}", f"<loc>{BASE_URL}{path}</loc>" in sitemap)

    feed = (out / "index.xml").read_text(encoding="utf-8")
    r.check("RSS feed is still generated", "<rss" in feed and "<item>" in feed)

    robots = (out / "robots.txt").read_text(encoding="utf-8")
    r.check("robots.txt still points at the sitemap", f"{BASE_URL}/sitemap.xml" in robots)


def main():
    if len(sys.argv) != 2:
        print("usage: check_build.py <build-directory>", file=sys.stderr)
        return 2
    out = Path(sys.argv[1])
    if not (out / "index.html").is_file():
        print(f"no build found at {out}", file=sys.stderr)
        return 2

    r = Results()
    check_home(out, r)
    check_404(out, r)
    check_openapi(out, r)
    check_llms_txt(out, r)
    check_structured_data(out, r)
    check_discovery_links(out, r)
    check_regressions(out, r)

    print(f"\n{r.passed} passed, {len(r.failures)} failed")
    for name, detail in r.failures:
        print(f"  FAILED: {name} {detail}")
    return 1 if r.failures else 0


if __name__ == "__main__":
    sys.exit(main())
