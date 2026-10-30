#!/usr/bin/env python3
"""Check the generated guides before publishing.

- every page has a title, a meta description, a canonical URL and valid JSON-LD
- every internal link points at a file that exists
- the sitemap and llms.txt list every guide, and nothing that doesn't exist
- each guide's ceremony count matches the app data it was built from
- no page publishes task text (only task counts)

Usage: python3 tools/check_site.py [path/to/laddo-this]
Exits non-zero on the first category with failures.
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_guides as bg  # noqa: E402

SITE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
failures = []


def fail(msg):
    failures.append(msg)


def local_path(href):
    """Map /laddothis-site/... or a full site URL to a file in the repo, or None for external links."""
    if href.startswith(bg.SITE):
        href = bg.BASE + href[len(bg.SITE):]
    if not href.startswith(bg.BASE + "/"):
        return None
    rel = href[len(bg.BASE) + 1:].split("#")[0]
    path = os.path.join(SITE_DIR, rel)
    return os.path.join(path, "index.html") if rel == "" or rel.endswith("/") else path


def main():
    data = bg.load_all(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/laddo-this"))
    pages = sorted(glob.glob(os.path.join(SITE_DIR, "guides", "**", "index.html"), recursive=True))
    guide_pages = [p for p in pages if os.path.dirname(p) != os.path.join(SITE_DIR, "guides")]
    if len(guide_pages) != len(bg.COMMUNITIES):
        fail(f"expected {len(bg.COMMUNITIES)} guide pages, found {len(guide_pages)}")

    task_texts = set()
    models = os.path.join(os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/laddo-this"), "LaddoThis", "Models")
    for f in glob.glob(os.path.join(models, "*Defaults.swift")):
        task_texts.update(t for t in re.findall(r'EventTask\(title:\s*"((?:[^"\\]|\\.)*)"', open(f).read()) if len(t) > 40)
    # A task title that also appears in a published description is description text, not a leaked checklist.
    published = " ".join(ev["description"] + " " + ev["significance"] + " " + ev["short"]
                         for evs in data.values() for ev in evs)
    task_texts = {t for t in task_texts if t not in published}

    for p in pages + [os.path.join(SITE_DIR, "index.html")]:
        s = open(p, encoding="utf-8").read()
        name = os.path.relpath(p, SITE_DIR)
        if p.startswith(os.path.join(SITE_DIR, "guides")):
            for tag in ("<title>", 'name="description"', 'rel="canonical"'):
                if tag not in s:
                    fail(f"{name}: missing {tag}")
            for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
                try:
                    json.loads(block)
                except ValueError as err:
                    fail(f"{name}: bad JSON-LD ({err})")
            leaked = [t for t in task_texts if t in s]
            if leaked:
                fail(f"{name}: publishes task text, e.g. {leaked[0][:60]!r}")
        for href in re.findall(r'(?:href|src)="([^"]+)"', s):
            target = local_path(href)
            if target and not os.path.exists(target):
                fail(f"{name}: broken link {href}")

    for raw, (page_name, slug, _) in bg.COMMUNITIES.items():
        p = os.path.join(SITE_DIR, "guides", f"{slug}-wedding-ceremonies", "index.html")
        if not os.path.exists(p):
            continue
        n = len(re.findall(r'<section id="c\d+">', open(p, encoding="utf-8").read()))
        if n != len(data[raw]):
            fail(f"{slug}: {n} ceremonies on the page, {len(data[raw])} in the app data")

    listed = set(re.findall(r"<loc>([^<]+)</loc>", open(os.path.join(SITE_DIR, "sitemap.xml")).read()))
    llms = open(os.path.join(SITE_DIR, "llms.txt")).read()
    for raw, (_, slug, _) in bg.COMMUNITIES.items():
        url = f"{bg.SITE}/guides/{slug}-wedding-ceremonies/"
        if url not in listed:
            fail(f"sitemap missing {url}")
        if url not in llms:
            fail(f"llms.txt missing {url}")
    for url in listed:
        if not os.path.exists(local_path(url)):
            fail(f"sitemap lists missing page {url}")

    if failures:
        print("\n".join(failures))
        print(f"\n{len(failures)} problem(s)")
        sys.exit(1)
    print(f"ok: {len(guide_pages)} guides, {sum(len(v) for v in data.values())} ceremonies, {len(listed)} sitemap URLs")


if __name__ == "__main__":
    main()
