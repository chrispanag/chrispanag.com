#!/usr/bin/env python3
"""Verify a deployed site's agent-facing endpoints over HTTP.

    ./tests/check_live.py                      # https://chrispanag.com
    ./tests/check_live.py https://staging.example.com

tests/run.sh checks what the build produces; this checks what the edge actually
serves, which is the only place status codes, content types and Vary headers exist.
Deploys are out of band (DigitalOcean App Platform), so run this after one lands.

Three checks are reported as PENDING rather than failures, because this repo cannot
make them true on its own: markdown content negotiation and JSON error responses need
an edge change, and the sparse home page is a deliberate design decision. See the notes
printed alongside them. The exit code covers the real checks only.

Shared parsing and constants live in common.py. Standard library only.
"""

import json
import sys
import urllib.error
import urllib.request

from common import (BASE_URL, INDEX_FILES, MAX_404_BYTES, RECOVERY_TARGETS, Page,
                    Report, check_llms_shape, check_person_node, graph_nodes, json_ld)

# Long enough to be unmistakably absent, stable enough to be reproducible.
MISSING_PATH = "/this-path-does-not-exist-agent-readiness-check"

USER_AGENT = "chrispanag.com-endpoint-check"


def fetch(url, accept=None, method="GET"):
    """Return (status, headers, body). Never raises on an HTTP error status."""
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    request = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers), exc.read()


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else BASE_URL).rstrip("/")
    r = Report()
    print(f"checking {base}\n")

    print("home page")
    status, headers, body = fetch(base + "/")
    html = body.decode("utf-8", "replace")
    page = Page(html)
    r.check("GET / returns 200", status == 200, f"got {status}")
    r.check("serves text/html", "text/html" in headers.get("Content-Type", ""))
    r.check("has an h1 in the raw HTML", bool(page.h1s), f"got {page.h1s!r}")
    r.note(
        "500+ characters of text without JavaScript",
        len(page.text) >= 500,
        f"got {len(page.text)}. The home page is deliberately the bare profile card, "
        "which is the site's visual identity, so it carries little text for crawlers. "
        "The content an agent needs is one hop away in /llms.txt and /index.json, both "
        "linked from every page via rel=describedby.",
    )

    print("\nhome page structured data")
    ld = json_ld(html)
    r.check("home serves one JSON-LD block", len(ld) == 1, f"got {len(ld)}")
    by_type = graph_nodes(ld)
    has_both = {"ProfilePage", "Person"} <= set(by_type)
    r.check("declares a ProfilePage and a Person", has_both, f"got {list(by_type)}")
    if has_both:
        check_person_node(r, by_type["Person"])

    print("\nmachine-readable files")
    bodies = {}
    for path, want_type in INDEX_FILES.items():
        status, headers, body = fetch(base + path)
        bodies[path] = body
        content_type = headers.get("Content-Type", "")
        r.check(f"GET {path} returns 200", status == 200, f"got {status}")
        r.check(f"{path} serves {want_type}", want_type in content_type,
                f"got {content_type!r}")

    print("\nopenapi.json contents")
    try:
        spec = json.loads(bodies["/openapi.json"])
        r.check("parses as JSON", True)
        r.check("is OpenAPI 3.1", str(spec.get("openapi", "")).startswith("3.1"))
        r.check("declares paths", bool(spec.get("paths")))
        served = spec.get("servers", [{}])[0].get("url", "")
        r.check("servers[0].url matches this host", served.rstrip("/") == base,
                f"got {served!r}")
    except (json.JSONDecodeError, IndexError) as exc:
        r.check("parses as JSON", False, str(exc))

    print("\nllms.txt contents")
    links = check_llms_shape(r, bodies["/llms.txt"].decode("utf-8", "replace"))
    r.check("lists pages", bool(links))
    broken = []
    for link in links:
        status, _, _ = fetch(link, method="HEAD")
        if status != 200:
            broken.append(f"{link} -> {status}")
    r.check("every llms.txt link returns 200", not broken, "; ".join(broken))

    print("\n404 handling")
    status, _, body = fetch(base + MISSING_PATH)
    text = body.decode("utf-8", "replace")
    r.check("unknown path returns 404", status == 404, f"got {status}")
    r.check("404 body is not an app shell", len(body) < MAX_404_BYTES,
            f"got {len(body)} bytes")
    for target in RECOVERY_TARGETS:
        r.check(f"404 body points at {target}", target in text)

    print("\nedge behavior (needs a change outside this repo)")
    _, headers, _ = fetch(base + "/", accept="text/markdown")
    content_type = headers.get("Content-Type", "")
    vary = headers.get("Vary", "")
    r.note(
        "Accept: text/markdown returns text/markdown",
        "text/markdown" in content_type,
        f"got {content_type!r}. A static origin cannot negotiate. Enable Cloudflare "
        "Rules -> Settings -> Markdown for Agents, which converts at the edge. "
        "See https://developers.cloudflare.com/fundamentals/reference/markdown-for-agents/",
    )
    r.note(
        "Vary includes Accept",
        "accept" in [v.strip().lower() for v in vary.split(",")],
        f"got Vary: {vary!r}. Without it a CDN can serve the cached HTML variant to an "
        "agent asking for markdown. The same Cloudflare toggle sets it.",
    )
    _, headers, _ = fetch(base + MISSING_PATH, accept="application/json")
    content_type = headers.get("Content-Type", "")
    r.note(
        "JSON Accept on an error returns JSON",
        "application/json" in content_type,
        f"got {content_type!r}. This site has no application server and DigitalOcean "
        "App Platform allows a single static error document, so an error can only be "
        "rendered as JSON by an edge function (Cloudflare Worker) in front of it.",
    )

    return r.summary()


if __name__ == "__main__":
    sys.exit(main())
