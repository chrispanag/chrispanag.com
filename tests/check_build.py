#!/usr/bin/env python3
"""Assertions over a built Hugo site (the ./public tree).

Run through tests/run.sh, which does the build first. These cover the agent-readiness
behavior added in layouts/404.html, layouts/home.llms.txt, layouts/home.openapi.json and
layouts/_partials/templates/schema_json.html, plus regression guards on the outputs
those changes touch (search index, sitemap, feed, home page metadata).

Shared parsing and constants live in common.py. Standard library only.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from common import (BASE_URL, INDEX_FILES, MAX_404_BYTES, RECOVERY_TARGETS,
                    Page, Report, check_llms_shape, check_person_node,
                    graph_nodes, is_alias_stub, json_ld)

SITE_TITLE = "Christos Panagiotakopoulos"

# The openapi.json entry that stands for everything else, and promises it 404s.
CATCH_ALL_PATH = "/{path}"

# The error document. It is a real 200 at its own address, but the spec describes it
# through the 404 responses on the paths above rather than as a path of its own.
ERROR_DOCUMENT = "/404.html"


def local_path(out: Path, url: str):
    """Map a site URL onto the file the build actually wrote, or None.

    "/about" and "/about/" both resolve, because that is what the host does: App
    Platform serves about/index.html for both spellings.
    """
    path = urlsplit(url).path.lstrip("/")
    for candidate in (out / path, out / path / "index.html"):
        if candidate.is_file():
            return candidate
    return None


def real_pages(out: Path):
    """Every page the build serves, as (file, site URL, html).

    Alias stubs are skipped: pagination.disableAliases is false, so Hugo writes a
    meta-refresh stub for /posts/page/1/ and every taxonomy equivalent, and those are
    redirects rather than pages. 404.html is included, under /404.html.
    """
    for page_path in sorted(out.glob("**/*.html")):
        html = page_path.read_text(encoding="utf-8")
        if is_alias_stub(html):
            continue
        if page_path.name == "index.html":
            directory = page_path.parent.relative_to(out).as_posix()
            url = "/" if directory == "." else f"/{directory}/"
        else:
            url = "/" + page_path.relative_to(out).as_posix()
        yield page_path, url, html


def path_pattern(template: str):
    """An OpenAPI path template as a regex, where {name} matches one path segment."""
    literals = [re.escape(part) for part in re.split(r"\{[^}]*\}", template)]
    return re.compile("^" + "[^/]+".join(literals) + "$")


def check_home(out: Path, r: Report):
    print("\nhome page (PaperMod profile card, deliberately minimal)")
    html = (out / "index.html").read_text(encoding="utf-8")
    page = Page(html)

    r.equal("exactly one h1", len(page.h1s), 1)
    r.check("h1 is the site name", page.h1s[:1] == [SITE_TITLE], f"got {page.h1s!r}")

    # Structural, not a copy of the wording: the job title and employer are already
    # stated in params.schema, params.profileMode.subtitle and the About timeline, and
    # pinning the exact string here would make a promotion fail the tests.
    r.check("profile card renders", 'class="profile"' in html or "class=profile" in html)
    r.check("profile buttons render", html.count("class=button") >= 3
            or html.count('class="button"') >= 3)

    # Scoped to the card, because a bare `"<span>" in html` matches the footer and so
    # can never fail. profileMode.subtitle is markdown, so also assert it was rendered
    # rather than printed as "[Prelude](https://prelude.so)".
    card = re.search(r"profile_inner(.*?)social-icons", html, re.S)
    r.check("profile subtitle renders", bool(card) and "<span>" in card.group(1),
            "no subtitle span between the profile card and its social icons")
    r.check("profile subtitle markdown is rendered, not literal",
            bool(card) and "](" not in card.group(1),
            f"got {card.group(1)!r}" if card else "")

    # The home page is the profile card and nothing else: no body copy below the hero,
    # none added inside the card. That is a deliberate design decision, and it outranks
    # the crawler heuristic that wants 500+ characters of text on `/`. Anything that
    # would satisfy that heuristic has to be visible, so it cannot be added without
    # changing the design; check_live.py reports it as PENDING.
    r.check("nothing renders below the profile card", "post-content" not in html,
            "the home page is meant to be the profile card only")
    r.check("no prose added inside the profile card", "profile-bio" not in html,
            "the card is meant to stay name + subtitle + icons + buttons")

    # The real invariant is that all three descriptions come from site config rather
    # than a page .Summary. Asserting they agree cross-checks three templates against
    # each other, and unlike a pinned literal it survives an edit to the config value.
    described = page.meta(name="description")
    r.check("meta description is set", bool(described))
    r.equal("og:description matches meta description",
            page.meta(property="og:description"), described)
    r.equal("twitter:description matches meta description",
            page.meta(name="twitter:description"), described)
    r.equal("<title> is the site title", page.title, SITE_TITLE)


def check_404(out: Path, r: Report, index_links):
    print("\n404 page (layouts/404.html)")
    raw = (out / "404.html").read_bytes()
    page = Page(raw.decode("utf-8"))

    r.check(f"body stays under {MAX_404_BYTES} bytes", len(raw) < MAX_404_BYTES,
            f"got {len(raw)} bytes")
    r.check("has an h1", len(page.h1s) == 1, f"got {page.h1s!r}")
    r.check("is not an alias stub", not is_alias_stub(raw.decode("utf-8")))

    # GET /404.html is itself a 200 that self-canonicalizes, so without a noindex the
    # error document is indexable like any other page. See extend_head.html. Read every
    # robots tag: the theme emits its own "index, follow" first.
    robots = [tag.get("content", "") for tag in page.metas if tag.get("name") == "robots"]
    r.check("is marked noindex", any("noindex" in value for value in robots),
            f"got {robots!r}")

    # The recovery links an agent needs, taken from what openapi.json declares rather
    # than a second hand-written list: the spec is the site's statement of its
    # machine-readable surface, so let it be the only one.
    for path in sorted(index_links):
        r.check(f"links to {path}", BASE_URL + path in page.links)

    # Every page in the nav, spelled canonically (with the trailing slash).
    for path in ("/", "/about/", "/chrispanag-on-the-web/", "/posts/", "/search/"):
        r.check(f"links to {path}", BASE_URL + path in page.links)

    # Nothing is worse than a recovery page whose own links 404.
    broken = [href for href in page.links
              if href.startswith(BASE_URL) and local_path(out, href) is None]
    r.check("every link resolves to a built file", not broken, f"broken: {broken}")


def check_openapi(out: Path, r: Report):
    """Assert the spec, and return the paths it tags as machine-readable indexes."""
    print("\nopenapi.json (layouts/home.openapi.json)")
    path = out / "openapi.json"
    if not path.is_file():
        r.check("openapi.json exists", False, "file not written")
        return set()

    raw = path.read_text(encoding="utf-8")
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as exc:
        r.check("openapi.json is valid JSON", False, str(exc))
        return set()
    r.check("openapi.json is valid JSON", True)

    # It must not be the search index: both are .json on the home page, and an earlier
    # template name made Hugo resolve this output format to layouts/index.json.
    is_doc = isinstance(spec, dict)
    r.check("is an OpenAPI document, not the search index", is_doc)
    if not is_doc:
        return set()

    r.check("openapi version is 3.1.x", str(spec.get("openapi", "")).startswith("3.1"))
    info = spec.get("info", {})
    for field in ("title", "version", "description"):
        r.check(f"info.{field} is set", bool(info.get(field)))
    r.equal("servers[0].url has no trailing slash",
            (spec.get("servers") or [{}])[0].get("url"), BASE_URL)

    paths = spec.get("paths", {})
    r.check("declares paths", bool(paths))
    r.check("every path starts with /", all(p.startswith("/") for p in paths),
            f"bad: {[p for p in paths if not p.startswith('/')]}")

    missing_responses = [f"{method} {p}" for p, item in paths.items()
                         for method, op in item.items() if not op.get("responses")]
    r.check("every operation declares responses", not missing_responses,
            f"{missing_responses}")

    ids = [op.get("operationId") for item in paths.values() for op in item.values()]
    r.check("operationIds are unique and present",
            all(ids) and len(ids) == len(set(ids)), f"{ids}")

    # Every $ref must resolve inside the document.
    unresolved = []
    for ref in re.findall(r'"\$ref"\s*:\s*"([^"]+)"', raw):
        node = spec
        for part in ref.removeprefix("#/").split("/"):
            node = node.get(part) if isinstance(node, dict) else None
            if node is None:
                unresolved.append(ref)
                break
    r.check("every $ref resolves", not unresolved, f"unresolved: {unresolved}")

    # The spec describes this site, so each concrete path must be something the build
    # really wrote. Templated paths (/{path}, /posts/{slug}/) are checked separately.
    missing = [p for p in paths if "{" not in p and local_path(out, BASE_URL + p) is None]
    r.check("every concrete path exists in the build", not missing, f"missing: {missing}")

    # And the other direction, which is the one that bites. CATCH_ALL_PATH promises a
    # 404 for anything the spec does not list, so a page the build really serves but
    # the spec omits turns that promise into a false statement. Checking only that
    # documented paths exist is what let /search/ and the taxonomy pages slip through.
    covered = [path_pattern(p) for p in paths if p != CATCH_ALL_PATH]
    undocumented = [url for _, url, _ in real_pages(out)
                    if url != ERROR_DOCUMENT
                    and not any(pattern.match(url) for pattern in covered)]
    r.check("every page in the build is documented", not undocumented,
            f"undocumented: {undocumented}")

    # The slug enum must match the posts on disk, or agents get 404s from the spec.
    slugs = set()
    for item in paths.get("/posts/{slug}/", {}).values():
        for param in item.get("parameters", []):
            if param.get("name") == "slug":
                slugs = set(param.get("schema", {}).get("enum", []))
    r.equal("slug enum matches the built posts", slugs,
            {p.parent.name for p in (out / "posts").glob("*/index.html")})

    # The 404 contract this site actually implements has to be in the spec.
    r.check("documents a 404 for unknown paths",
            "404" in paths.get(CATCH_ALL_PATH, {}).get("get", {}).get("responses", {}))

    indexes = {p for p, item in paths.items()
               for op in item.values() if "indexes" in op.get("tags", [])}
    r.equal("tags every machine-readable index", indexes, set(INDEX_FILES))
    return indexes - {"/robots.txt"}


def check_llms_txt(out: Path, r: Report):
    print("\nllms.txt (layouts/home.llms.txt, llmstxt.org v2 format)")
    text = (out / "llms.txt").read_text(encoding="utf-8")
    links = check_llms_shape(r, text)

    lines = [ln for ln in text.splitlines() if ln.strip()]
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

    r.check("has link entries", bool(links))
    r.check("every link is an absolute URL",
            all(link.startswith("https://") for link in links),
            f"relative: {[l for l in links if not l.startswith('https://')]}")
    broken = [link for link in links if local_path(out, link) is None]
    r.check("every link resolves to a built file", not broken, f"broken: {broken}")
    r.check("points at openapi.json", f"{BASE_URL}/openapi.json" in links)


def check_structured_data(out: Path, r: Report):
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

    by_type = graph_nodes(blocks)
    r.check("home graph has a ProfilePage", "ProfilePage" in by_type, f"got {list(by_type)}")
    r.check("home graph has a Person", "Person" in by_type, f"got {list(by_type)}")
    if not {"ProfilePage", "Person"} <= set(by_type):
        return

    profile, person = by_type["ProfilePage"], by_type["Person"]
    r.equal("ProfilePage.mainEntity points at the Person",
            profile.get("mainEntity", {}).get("@id"), person.get("@id"))

    check_person_node(r, person)
    r.equal("Person.image agrees with og:image",
            person.get("image"), page.meta(property="og:image"))
    for field in ("homeLocation", "knowsAbout"):
        r.check(f"Person.{field} is set", bool(person.get(field)))
    r.check("Person.worksFor is an Organization with a url",
            person.get("worksFor", {}).get("@type") == "Organization"
            and person.get("worksFor", {}).get("url", "").startswith("https://"),
            f"got {person.get('worksFor')!r}")

    # The rest of that partial is the theme's code, carried over verbatim by the fork.
    # If a PaperMod bump is re-synced badly, these are what break first.
    post = next(iter(sorted((out / "posts").glob("*/index.html"))), None)
    r.check("a post page exists to check", post is not None)
    if post:
        types = [n.get("@type") for n in json_ld(post.read_text(encoding="utf-8"))]
        r.check("posts still emit BreadcrumbList and BlogPosting",
                {"BreadcrumbList", "BlogPosting"} <= set(types), f"got {types}")
    section = json_ld((out / "posts" / "index.html").read_text(encoding="utf-8"))
    r.check("sections still emit BreadcrumbList",
            "BreadcrumbList" in [n.get("@type") for n in section])


def check_discovery_links(out: Path, r: Report):
    print("\ndiscovery links in <head> (layouts/_partials/extend_head.html)")
    missing_described, missing_service, pages = [], [], []
    # real_pages covers 404.html too, which is the page an agent is likeliest to land
    # on by accident and so the one that most needs the discovery links.
    for page_path, url, html in real_pages(out):
        pages.append(page_path)
        page = Page(html)
        if page.link("describedby") != f"{BASE_URL}/llms.txt":
            missing_described.append(url)
        if page.link("service-desc") != f"{BASE_URL}/openapi.json":
            missing_service.append(url)

    r.check("build produced HTML pages", bool(pages))
    r.check("every page links rel=describedby to llms.txt", not missing_described,
            f"{missing_described[:5]}")
    r.check("every page links rel=service-desc to openapi.json", not missing_service,
            f"{missing_service[:5]}")


def check_regressions(out: Path, r: Report):
    print("\nunchanged outputs (regression guards)")

    # Search: config.yml's outputs.home must keep JSON, and the shape Fuse.js indexes.
    index = json.loads((out / "index.json").read_text(encoding="utf-8"))
    r.check("index.json is a non-empty array", isinstance(index, list) and bool(index))
    r.check("index.json entries keep the Fuse.js keys",
            all({"title", "content", "permalink", "summary"} <= set(e) for e in index))
    # The home page is not a RegularPage, so it must not appear in search.
    r.check("home page did not enter the search index",
            all(e["permalink"].rstrip("/") != BASE_URL for e in index))

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

    r = Report()
    check_home(out, r)
    index_links = check_openapi(out, r)
    check_404(out, r, index_links or RECOVERY_TARGETS)
    check_llms_txt(out, r)
    check_structured_data(out, r)
    check_discovery_links(out, r)
    check_regressions(out, r)
    return r.summary()


if __name__ == "__main__":
    sys.exit(main())
