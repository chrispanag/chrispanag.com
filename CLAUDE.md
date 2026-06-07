# chrispanag.com

Personal blog/portfolio for Christos Panagiotakopoulos, built with **Hugo** (extended)
and the **PaperMod** theme. Static site, deployed at https://chrispanag.com/.

## Commands

```bash
git submodule update --init --recursive   # REQUIRED first — theme is a submodule (see Gotchas)
hugo server -D                            # local dev at :1313, -D includes drafts
hugo                                      # production build → ./public
hugo new posts/<slug>/index.md            # new post (archetype sets draft: true)
```

Requires **Hugo extended** (`brew install hugo`). Built/tested with v0.162.1+extended.

## Architecture

- `config.yml` — site config (YAML, **not** the Hugo default `config.toml`).
- `content/` — all content as Hugo **page bundles** (a directory + `index.md`):
  - `posts/<slug>/index.md` — blog posts, with cover/images co-located in the same dir.
  - `about/index.md` — the About page bundle; co-locates `profile.jpeg`, rendered as a
    circular portrait by the `{{< profile-photo >}}` shortcode (resized + fingerprinted).
  - `chrispanag-on-the-web/` — standalone single page.
- `archetypes/default.md` — template for `hugo new` (defaults `draft: true`).
- `static/` — favicons, profile image; served at site root.
- `themes/PaperMod/` — theme, pinned as a **git submodule** (not vendored).

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
- The home page emits a custom **`llms.txt`** plain-text output (`outputFormats.llms`
  + `outputs.home` in `config.yml`), alongside HTML and RSS.
- **Site search** needs `JSON` in `outputs.home` (generates `index.json`) plus
  `content/search.md` with `layout: search`. Don't drop `JSON` from `outputs.home`.
