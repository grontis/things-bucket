#!/usr/bin/env python3
"""
Generates index.html by walking the repo for .html files.

- Groups pages by top-level folder (root-level files go under "General").
- Uses each file's <title> tag as its display name, falling back to the filename.
- Adds a last-updated date per page (from git history when available).
- Zero dependencies: Python 3 stdlib only.

Run from the repo root:  python3 generate_index.py
"""

import html
import os
import re
import subprocess
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT = REPO_ROOT / "index.html"

# Directories to skip entirely
SKIP_DIRS = {".git", ".github", "node_modules", "assets", "static"}
# Files to skip (the index itself, and any folder-level index pages are still listed
# as folder links, not duplicated as pages)
SKIP_FILES = {"index.html"}

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def find_pages():
    pages = []
    for path in sorted(REPO_ROOT.rglob("*.html")):
        rel = path.relative_to(REPO_ROOT)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if rel.name in SKIP_FILES and len(rel.parts) == 1:
            continue  # skip only the root index.html; folder index.html is kept
        pages.append(rel)
    return pages


def page_title(rel):
    try:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        m = TITLE_RE.search(text[:4000])
        if m:
            title = html.unescape(re.sub(r"\s+", " ", m.group(1)).strip())
            if title:
                return title
    except OSError:
        pass
    # Fallback: prettify the filename
    name = rel.stem.replace("-", " ").replace("_", " ").strip()
    return name.title() if name else rel.name


def last_updated(rel):
    """Date of last commit touching this file; falls back to today for new files."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", str(rel)],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=10,
        )
        d = out.stdout.strip()
        if d:
            return d
    except (OSError, subprocess.SubprocessError):
        pass
    return date.today().isoformat()


def group_pages(pages):
    """Return {group_name: [(title, href, date), ...]} keyed by top-level folder."""
    groups = {}
    for rel in pages:
        group = rel.parts[0] if len(rel.parts) > 1 else "General"
        group = group.replace("-", " ").replace("_", " ").title()
        href = "/".join(rel.parts)  # relative URL works on any Pages base path
        groups.setdefault(group, []).append((page_title(rel), href, last_updated(rel)))
    # "General" first, then alphabetical; pages sorted by title within each group
    ordered = {}
    for key in sorted(groups, key=lambda k: (k != "General", k.lower())):
        ordered[key] = sorted(groups[key], key=lambda p: p[0].lower())
    return ordered


def render(groups):
    total = sum(len(v) for v in groups.values())
    sections = []
    for name, pages in groups.items():
        items = "\n".join(
            f'        <li><a href="{html.escape(href)}">'
            f'<span class="t">{html.escape(title)}</span>'
            f'<span class="d">{d}</span></a></li>'
            for title, href, d in pages
        )
        sections.append(
            f'    <section>\n'
            f'      <h2>{html.escape(name)} <span class="n">{len(pages)}</span></h2>\n'
            f'      <ul>\n{items}\n      </ul>\n'
            f'    </section>'
        )
    body = "\n".join(sections)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pages</title>
<style>
  :root {{
    --paper: #fbfaf7;
    --ink: #1c1b18;
    --muted: #8a8578;
    --line: #e6e2d8;
    --accent: #2456d6;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--paper);
    color: var(--ink);
    font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}
  main {{ max-width: 640px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }}
  header h1 {{
    font-size: 1.4rem; letter-spacing: -0.01em; margin: 0 0 .25rem;
  }}
  header p {{
    margin: 0 0 1.25rem; color: var(--muted);
    font: 12px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace;
    text-transform: uppercase; letter-spacing: .08em;
  }}
  #q {{
    width: 100%; padding: .65rem .8rem; margin-bottom: 1.75rem;
    font: inherit; color: var(--ink);
    background: #fff; border: 1px solid var(--line); border-radius: 8px;
  }}
  #q:focus {{ outline: 2px solid var(--accent); outline-offset: 1px; border-color: transparent; }}
  section {{ margin-bottom: 1.75rem; }}
  h2 {{
    font-size: .8rem; text-transform: uppercase; letter-spacing: .1em;
    color: var(--muted); margin: 0 0 .4rem;
    border-bottom: 1px solid var(--line); padding-bottom: .4rem;
  }}
  h2 .n {{ font-weight: 400; opacity: .7; }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  li a {{
    display: flex; justify-content: space-between; align-items: baseline; gap: 1rem;
    padding: .55rem .25rem; text-decoration: none; color: inherit;
    border-bottom: 1px solid transparent;
  }}
  li a:hover .t, li a:focus-visible .t {{ color: var(--accent); text-decoration: underline; }}
  li a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 1px; border-radius: 4px; }}
  .t {{ min-width: 0; overflow-wrap: anywhere; }}
  .d {{
    flex-shrink: 0; color: var(--muted);
    font: 11px/1 ui-monospace, SFMono-Regular, Menlo, monospace;
  }}
  li.hide, section.hide {{ display: none; }}
  #none {{ display: none; color: var(--muted); }}
</style>
</head>
<body>
<main>
  <header>
    <h1>Pages</h1>
    <p>{total} page{"s" if total != 1 else ""} · updated {date.today().isoformat()}</p>
  </header>
  <input id="q" type="search" placeholder="Filter pages…" aria-label="Filter pages">
{body}
  <p id="none">No pages match.</p>
</main>
<script>
  const q = document.getElementById('q');
  q.addEventListener('input', () => {{
    const term = q.value.trim().toLowerCase();
    let any = false;
    document.querySelectorAll('section').forEach(sec => {{
      let vis = 0;
      sec.querySelectorAll('li').forEach(li => {{
        const hit = !term || li.textContent.toLowerCase().includes(term);
        li.classList.toggle('hide', !hit);
        if (hit) vis++;
      }});
      sec.classList.toggle('hide', vis === 0);
      any = any || vis > 0;
    }});
    document.getElementById('none').style.display = any ? 'none' : 'block';
  }});
</script>
</body>
</html>
"""


def main():
    pages = find_pages()
    groups = group_pages(pages)
    OUTPUT.write_text(render(groups), encoding="utf-8")
    print(f"Wrote index.html with {sum(len(v) for v in groups.values())} pages "
          f"in {len(groups)} group(s).")


if __name__ == "__main__":
    main()