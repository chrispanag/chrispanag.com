# chrispanag.com

My personal site and blog, live at <https://chrispanag.com/>. Built with
[Hugo](https://gohugo.io/) (extended) and the
[PaperMod](https://github.com/adityatelange/hugo-PaperMod) theme.

Feel free to poke around, borrow ideas, or open an issue if something looks broken.

## Running it locally

The theme is a git submodule, so clone it first or `hugo` will fail with an empty
`themes/PaperMod/`:

```bash
git clone https://github.com/chrispanag/chrispanag.com.git
cd chrispanag.com
git submodule update --init --recursive

hugo server -D    # http://localhost:1313, -D includes drafts
```

You need **Hugo extended** (`brew install hugo`), version **0.162 or newer**: some
shortcodes encode AVIF images, which older versions cannot do.

## Building and testing

```bash
hugo             # production build into ./public
./tests/run.sh   # build, then assert things about the output
```

`tests/` is plain Python 3 with no dependencies. It checks the layout of the home page,
the structured data, the 404 page, and that `/openapi.json` matches what the build
actually serves.

## Layout

- `config.yml` - site config (YAML, not the Hugo default TOML).
- `content/` - posts and pages, each one a Hugo page bundle with its images alongside.
- `layouts/` - project overrides of theme templates, plus a few custom shortcodes.
- `assets/css/extended/` - custom CSS on top of PaperMod.
- `tests/` - build and live-site checks.

## A note on agents

The site tries to be pleasant for AI crawlers and agents as well as people: it serves
[`/llms.txt`](https://chrispanag.com/llms.txt) as a plain-text index and
[`/openapi.json`](https://chrispanag.com/openapi.json) as a description of its
machine-readable endpoints, and every page links to both. `CLAUDE.md` documents the
details for anyone (or anything) working in the repo.

## Deployment

The site is deployed on DigitalOcean App Platform, built from this repo by its Hugo
buildpack. The Hugo version used in production is pinned in the app spec, not in this
repo.
