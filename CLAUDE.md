# chrispanag.com

Personal blog/portfolio for Christos Panagiotakopoulos, built with **Hugo** (extended)
and the **PaperMod** theme. Static site, deployed at https://chrispanag.com/.

## Commands

```bash
git submodule update --init --recursive   # REQUIRED first — theme is a submodule (see Gotchas)
hugo server -D                            # local dev at :1313, -D includes drafts
hugo                                      # production build → ./public
hugo new posts/<slug>/index.md            # new post (archetype sets draft: true)
./tests/run.sh                            # build + assert (see Agent readiness)
./tests/check_live.py [base-url]          # verify a deployed site over HTTP
```

Requires **Hugo extended** (`brew install hugo`). Built/tested with v0.165.0+extended.
**Hugo >= 0.162 is a hard floor**: the `photo` and `web-card` shortcodes emit AVIF, which
older versions cannot encode. Production pins its own version via the `HUGO_VERSION`
build-time env var in the DigitalOcean App Platform app spec — bump it there, not here.

## Architecture

- `config.yml` — site config (YAML, **not** the Hugo default `config.toml`).
- `content/` — all content as Hugo **page bundles** (a directory + `index.md`):
  - `posts/<slug>/index.md` — blog posts, with cover/images co-located in the same dir.
  - `about/index.md` — the About page bundle; co-locates `profile.jpeg`, rendered as a
    circular portrait by the `{{< profile-photo >}}` shortcode (resized + fingerprinted).
  - `chrispanag-on-the-web/index.md` — the "Me on the web" page: a card gallery of
    appearances + profile pills, built from co-located images and the `web-card` /
    `web-grid` / `web-profiles` / `web-link` shortcodes (see Content conventions).
- `archetypes/default.md` — template for `hugo new` (defaults `draft: true`).
- `layouts/` — project overrides of theme templates:
  - `404.html` — the recovery page (see Agent readiness).
  - `home.llms.txt` — adds the llmstxt.org blockquote and `## Optional` section, and
    calls the theme's section printer rather than copying it (see Gotchas).
  - `home.openapi.json` — generates `/openapi.json`.
  - `_partials/templates/schema_json.html` — **forked** from the theme; see Gotchas.
- `static/` — favicons, profile image; served at site root.
- `tests/` — `run.sh` builds and runs `check_build.py` over the output; `check_live.py`
  checks a deployed site over HTTP. Standard library only, no toolchain to install.
- `themes/PaperMod/` — theme, pinned as a **git submodule** (not vendored).

## Agent readiness

The site is tuned for AI crawlers and agents, and `tests/` encodes those guarantees.
When changing any of the following, run `./tests/run.sh`:

- The **home page is deliberately the bare profile card** — a full-viewport hero and
  nothing below it. That is the site's visual identity and outranks the crawler
  heuristic that wants 500+ characters of text on `/`; do not add body copy there.
  `tests/run.sh` asserts nothing renders below the profile card, and that no prose is
  added inside it. Agents get the content one hop away, via the `rel="describedby"`
  link to `/llms.txt`, and get the identity from the JSON-LD graph below.
- Because the home page says so little in prose, it says it in **JSON-LD** instead: a
  `ProfilePage` whose `mainEntity` is a fully described `Person` (job title, employer,
  location, `knowsAbout`, `sameAs`). The copy lives in `params.schema` in `config.yml`;
  keep it factual, it is a public claim about a real person. Note that the job title and
  employer are stated in **three** places that nothing keeps in sync: `params.schema`,
  `params.profileMode.subtitle`, and the About page timeline. Change all three together. This is invisible, so it
  does *not* satisfy heuristics that count rendered characters.
- **Unknown paths return a real 404** (DigitalOcean App Platform serves `404.html` as
  the error document) with a short body linking to the machine-readable indexes. Keep
  that body short and link-dense; a long one defeats its purpose.
- `/llms.txt` follows the **llmstxt.org v2 format**: H1, then a blockquote summary, then
  non-heading prose, then H2 file lists. Every file list sits under a heading.
- `/openapi.json` describes only endpoints that **really exist**; the tests fail if a
  documented path is not in the build, or if the post slug enum drifts.
- Every page carries `rel="describedby"` (llms.txt) and `rel="service-desc"`
  (openapi.json) from `layouts/_partials/extend_head.html`.

Two things **cannot** be fixed from this repo, because a static origin cannot negotiate
and App Platform allows a single error document: `Accept: text/markdown` content
negotiation with `Vary: Accept` (enable Cloudflare's *Markdown for Agents*, which does
it at the edge), and JSON error bodies (needs an edge function). `./tests/check_live.py`
reports both as PENDING with the fix, rather than failing.

## Content conventions

- Site copy is **American English, no em dashes**.
- New posts are page bundles: create `content/posts/<slug>/index.md` and put images
  in the same folder. Reference them with `cover.relative: true` / relative paths.
- Post front matter: `author`, `title`, `date`, `description`, `tags`, `categories`,
  optional `cover.image`. See existing posts for the pattern.
- The About page **timeline** is a custom component, not plain markdown: entries live
  inside `{{< timeline >}} … {{< /timeline >}}` in `content/about/index.md`, ordered oldest
  first, each as `**<Date>** <description>` with a bold date and **no trailing colon**
  (the date renders as a label). Component: `layouts/shortcodes/timeline.html` +
  `assets/css/extended/timeline.css`. To add an entry, use the `add-timeline-entry` skill.
- The **"Me on the web"** page (`content/chrispanag-on-the-web/index.md`) is a card
  gallery, not plain markdown: appearances are `{{< web-card >}}` entries inside
  `{{< web-grid >}}` (cover image, kicker, title, inline description), and profile
  links are `{{< web-link >}}` pills inside `{{< web-profiles >}}`. Co-locate cover
  images in the bundle; image-less cards fall back to a placeholder glyph. To add a
  link, use the `add-web-link` skill.

## Gotchas

- **Theme is a git submodule.** A fresh clone has an empty `themes/PaperMod/`, so
  `hugo` fails until `git submodule update --init --recursive`. The submodule is
  pinned to a specific commit.
- **Overriding theme partials:** copy into `layouts/_partials/<name>.html` (new
  template system — underscore, **not** `layouts/partials/`). Avoid forking a partial
  just to make nav/asset URLs relative: prod builds use absolute URLs by design
  (correct for canonical/OG), and `hugo server` rewrites `baseURL` to localhost for
  local preview. Preview with `hugo server`, not by static-serving `./public`.
- **`buildDrafts: false`** — drafts are excluded from production builds; preview them
  with `hugo server -D`.
- **`config.yml`, not TOML** — edit the YAML file; there is no `config.toml`.
- The home page emits custom **`llms.txt`** and **`openapi.json`** outputs
  (`outputFormats` + `outputs.home` in `config.yml`), alongside HTML, RSS and JSON.
- **Name custom output format templates `<kind>.<format>.<ext>`.** Both project
  templates do (`home.openapi.json`, `home.llms.txt`), for two separate reasons:
  - `layouts/openapi.json` does *not* work at all — Hugo matches it against the theme's
    `layouts/index.json`, and the `openapi` output silently becomes a copy of the
    search index.
  - `layouts/llms.txt` would work, but it **shadows** the theme's `layouts/llms.txt`,
    which means the theme's `{{ define "llms_print_section" }}` is never parsed and the
    project template has to carry its own copy of that recursive printer.
    `home.llms.txt` outranks the theme's file without hiding it, so the define stays
    callable and there is nothing to keep in sync.
- **Site search** needs `JSON` in `outputs.home` (generates `index.json`) plus
  `content/search.md` with `layout: search`. Don't drop `JSON` from `outputs.home`.
- **Markdown typography lives on `.md-content`, not `.post-content`.** Paragraph
  spacing, list styling and link underlines are all `.md-content` rules, so a custom
  template that renders prose must use the theme's own pair,
  `<div class="post-content md-content ...">`. With `post-content` alone the text
  renders as an unspaced wall with invisible links.
- **Building custom components on PaperMod:** components rendered inside `.post-content`
  must beat the theme's own rules — `.post-content img` adds `border-radius`/`margin`
  and `.md-content a` adds an underline, so scope overrides under `.post-content` /
  `.md-content` (a bare class loses on specificity). Reuse the theme's icon set with
  `{{ partial "svg.html" (dict "name" "github") }}` (unknown names fall back to a link glyph).
- **`layouts/_partials/templates/schema_json.html` is a fork, and needs re-syncing
  when the PaperMod submodule is bumped.** Only the `.IsHome` branch is ours;
  everything from `{{- else if (or .IsPage .IsSection) }}` onward is the theme's
  (BreadcrumbList + BlogPosting), carried verbatim. Diff that tail against the theme's
  file after a bump. `tests/run.sh` asserts posts and sections still emit their schema,
  which is what breaks first if the re-sync is missed. The fork exists because the home
  branch set `Person.image` to `favicon.ico` rather than the profile photo and carried
  almost no detail, and a partial cannot be overridden a branch at a time. (A
  `module.mounts` alias can avoid the fork by re-mounting the theme's file under another
  name, but declaring any mount replaces Hugo's defaults, so every source directory has
  to be restated in `config.yml` — traded away deliberately.)
- **Do not give `content/_index.md` a body.** Besides changing the home page design,
  it would hand the home page a `.Summary`, and PaperMod's opengraph and twitter_cards
  partials resolve `or .Description .Summary site.Params.description` — so the body
  would silently become the social description. `tests/run.sh` guards both.
