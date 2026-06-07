---
name: add-web-link
description: Add a link to the "Me on the web" page (content/chrispanag-on-the-web/index.md). Use when Christos wants to add a talk, podcast, interview, press feature, TV appearance, or profile to that page — e.g. "add a link to me on the web", "I was on a podcast, add it", "add this article to my press page", "put my Mastodon on the on-the-web page", "add X to me on the web".
---

# Add a link to "Me on the web"

The "Me on the web" page is a card gallery, not a plain markdown list. Adding a link
means writing one shortcode call in the right section. You do not need to touch the
component files (shortcodes or CSS) to add a link.

## Where it lives

`content/chrispanag-on-the-web/index.md`. It has three sections:

- `## Talks & podcasts` — video talks, panels, conference sessions, podcast episodes.
  Cards live inside a `{{< web-grid >}} … {{< /web-grid >}}` block.
- `## Interviews & press` — interviews, articles, TV segments. Also a `web-grid` block.
- `## Find me elsewhere` — profile links rendered as pills, inside a
  `{{< web-profiles >}} … {{< /web-profiles >}}` block.

Pick the section by medium. A new card goes inside that section's existing grid block,
as its own `{{< web-card >}}` call separated from its neighbors by a blank line. Order
within a section is loose; newest-first reads fine. Whether it lands left or right in the
grid is automatic, so don't worry about it.

## Adding a card (talks, podcasts, interviews, press, TV)

```
{{< web-card
    url="https://example.com/the-article"
    title="The headline as it should read on the card"
    kicker="Outlet name · Greek"
    image="outlet.jpg" >}}
One or two sentences on what it was, in plain prose.
{{< /web-card >}}
```

Parameters:
- **`url`** (required) — where the card links. Opens in a new tab.
- **`title`** (required) — the card heading. For non-English coverage, prefer a short,
  accurate English title over a transliterated headline (cleaner grid). If the title
  contains double quotes, escape them: `title="\"When is my bus coming\" on national TV"`.
- **`kicker`** (optional) — small uppercase label above the title. Use the outlet, venue,
  or format, and append `· Greek` (or other language) when the piece isn't in English:
  `NEARCON 2022 · Lisbon`, `Ready Layer One · Podcast`, `iEfimerida.gr · Greek`.
- **`image`** (optional but strongly preferred) — a co-located image filename (see below).
  Auto-cropped to a 16:9 cover and fingerprinted, so a wide landscape image works best.
- **`icon`** (optional) — only used when there is **no** image. Picks the placeholder
  glyph so it matches the medium: `article` (default), `tv`, `mic`, `play`, `globe`.
- **Inner content** — the description, in markdown, rendered inline. Keep it to a sentence
  or two. Do not put a markdown link inside it: the whole card is already a link, and a
  nested link breaks the HTML.

### Getting an image

Every card looks better with a cover. Co-locate the file in the page bundle directory
`content/chrispanag-on-the-web/` and reference it by bare filename (`image="outlet.jpg"`).

When the link is press coverage, pull the lead image from the source:

```bash
cd content/chrispanag-on-the-web
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
# find the article's social image
curl -sL -A "$UA" "<article-url>" | grep -oiE '<meta[^>]+property="og:image"[^>]*>'
# download it
curl -sL -A "$UA" -e "<article-domain>" "<image-url>" -o outlet.jpg
file outlet.jpg   # confirm it's a real JPEG/PNG and check the dimensions
```

Then **look at the image** before wiring it in (read it as an image), and check two things:
1. It's relevant and a wide-ish landscape (portrait phone screenshots crop to a thin band).
2. It isn't a near-duplicate of another card's image. Greek outlets often reuse the same
   stock photo as their `og:image`; if so, grab a different in-article photo instead
   (look for other `wp-content/uploads/…` or `/sites/…/files/…` URLs in the page source).

If you genuinely can't get a good image, omit `image=` and set `icon=` to match the medium.

## Adding a profile pill (Find me elsewhere)

```
{{< web-link name="Mastodon" url="https://mastodon.social/@chrispanag" icon="mastodon" >}}
```

Add it inside the `{{< web-profiles >}} … {{< /web-profiles >}}` block, one per line.

- **`name`** — label shown on the pill.
- **`url`** — destination.
- **`icon`** — a PaperMod SVG icon name (`github`, `linkedin`, `x`, `youtube`, `mastodon`,
  `instagram`, `rss`, …). Unknown names fall back to a generic link glyph, which is fine.
  The full set is in `themes/PaperMod/layouts/partials/svg.html`.

## Voice and copy

American English, no em dashes (repo-wide rule). Titles and descriptions stay concrete
and plain: say what the piece was and what it was about. Avoid AI-filler adjectives
("innovative", "seamless"). Keep descriptions to one or two sentences so cards stay even.

## After editing

Preview before committing:

```bash
hugo server -D   # then open http://localhost:1313/chrispanag-on-the-web/
```

Confirm the new card shows its cover (or a clean placeholder glyph), kicker, title, and
description, and that nothing else shifted. A clean `hugo` build (exit 0) is the final check.

If you removed a card that had its own image, delete the now-orphaned image file from the
bundle so it doesn't linger.

## Component files (reference only — not edited per link)

- `layouts/shortcodes/web-grid.html` / `web-card.html` — the grid and card.
- `layouts/shortcodes/web-profiles.html` / `web-link.html` — the profile pills.
- `assets/css/extended/web.css` — card, placeholder, and pill styling. PaperMod auto-loads
  any file under `assets/css/extended/`.
