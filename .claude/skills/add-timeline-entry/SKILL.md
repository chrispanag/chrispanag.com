---
name: add-timeline-entry
description: Add an entry to the career timeline on the About page (content/about.md). Use when Christos wants to add a job, milestone, project, launch, or life event to his timeline — e.g. "add a timeline entry", "I started a new role, put it on the about page", "add X to my timeline", "got promoted, update the timeline".
---

# Add a timeline entry

The timeline on the About page is a custom component, not plain markdown. Adding an
entry means writing one correctly-formatted paragraph in the right place. You do not
need to touch the component files (shortcode or CSS) to add an entry.

## Where it lives

`content/about.md`, inside the `{{< timeline >}} … {{< /timeline >}}` block under the
`## Timeline` heading. Entries are ordered **oldest first** (top) to newest (bottom).

## Entry format

One entry is one paragraph, separated from its neighbors by a blank line:

```
**<Date>** <description>
```

Rules:
- **Bold date, no trailing colon.** The CSS turns the leading `**bold**` into an
  uppercase label above the entry, so a colon would render as `SEP 2025:` and look
  wrong. Write `**Sep 2025**`, not `**Sep 2025:**`.
- **Date style:** `**Mon YYYY**` for a point in time (`**Feb 2022**`), or
  `**Mon YYYY - Mon YYYY**` for a range with spaces around the hyphen
  (`**Mar 2023 - Aug 2024**`). Match the existing capitalization (`Sep`, not `September`).
- **Place it in chronological order.** Find the two entries it falls between and insert
  it there, keeping a blank line on each side.
- **Link names on first mention.** Company, product, school, and project names get a
  markdown link the first time they appear (`[Prelude](https://prelude.so)`).
- **Press references**, if any, go at the end as
  `(press references: [Name](url), [Name](url))`.

## Voice

Match the rest of the page: concrete and builder-focused. Lead with what was designed,
built, shipped, or owned, and back it with scale or outcome numbers when you have them
(`over 1M req/s`, `20,000 weekly users`, `cut their running cost`). Christos's identity
on this page is builder and engineering leader aiming at head-of-engineering scope, so
frame leadership as owning technical direction and architecture while staying hands-on,
not as people management.

Keep the prose clean: no em dashes, no forced three-item lists, and avoid AI-filler
adjectives like "innovative", "robust", "seamless", "cutting-edge". State the work and
the result.

## Example

A new senior role added after the Sep 2025 entry:

```
**Jan 2027** Took over as Head of Engineering at [Prelude](https://prelude.so),
owning the technical direction and team across verification, anti-fraud, and platform.
```

## After editing

Preview before committing:

```bash
hugo server -D   # then open http://localhost:1313/about
```

The date should render as a gray uppercase label with a dot on the vertical line, and
the description below it. If the date shows a trailing colon, you left the `:` in the
bold; remove it.

## Component files (reference only — not edited per entry)

- `layouts/shortcodes/timeline.html` — wraps the block and renders its inner markdown.
- `assets/css/extended/timeline.css` — the vertical line, dots, and date-label styling.
  PaperMod auto-loads any file under `assets/css/extended/`.
