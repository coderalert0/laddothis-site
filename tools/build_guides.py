#!/usr/bin/env python3
"""Build the ceremony guides for the LaddoThis site from the app's own data.

Reads the community defaults in the app repo (LaddoThis/Models/*Defaults.swift)
and writes:
  guides/index.html                      hub page, all communities
  guides/<slug>/index.html               one page per community
  llms.txt                               plain-text summary for AI crawlers
  sitemap.xml

Pages publish ceremony names, order, timing, descriptions and significance.
Task lists stay in the app: pages show only how many tasks each checklist has.

Usage: python3 tools/build_guides.py [path/to/laddo-this]   (default ~/laddo-this)
"""
import datetime
import html
import json
import os
import re
import sys

SITE = "https://coderalert0.github.io/laddothis-site"
BASE = "/laddothis-site"
APP_ID = "6759238184"
APP_URL = f"https://apps.apple.com/app/id{APP_ID}"
# App Store campaign token so App Store Connect reports downloads from these pages.
APP_URL_TRACKED = f"https://apps.apple.com/app/apple-store/id{APP_ID}?pt=128557981&ct=web-guides&mt=8"
TODAY = datetime.date.today().isoformat()

# Events in the data that are planning aids, not ceremonies.
NOT_CEREMONIES = {"Wedding Day Personal Kit", "Planning & Paperwork"}

# community raw value -> (page name, slug, group). Raw values match WeddingCommunity in the app.
COMMUNITIES = {
    "Sikh Punjabi": ("Sikh Punjabi", "sikh-punjabi", "Punjabi"),
    "Hindu Punjabi": ("Hindu Punjabi", "hindu-punjabi", "Punjabi"),
    "Punjabi Muslim": ("Pakistani (Punjabi Muslim)", "pakistani-punjabi-muslim", "Pakistani and Muslim"),
    "Muhajir": ("Muhajir (Urdu-speaking Pakistani)", "muhajir", "Pakistani and Muslim"),
    "Sindhi Muslim": ("Sindhi Muslim", "sindhi-muslim", "Pakistani and Muslim"),
    "Saraiki": ("Saraiki", "saraiki", "Pakistani and Muslim"),
    "Pashtun": ("Pashtun", "pashtun", "Pakistani and Muslim"),
    "Balochi": ("Balochi", "balochi", "Pakistani and Muslim"),
    "North Indian Muslim": ("Indian Muslim (North Indian)", "indian-muslim", "Pakistani and Muslim"),
    "Kashmiri Muslim": ("Kashmiri Muslim", "kashmiri-muslim", "Pakistani and Muslim"),
    "Ismaili": ("Ismaili", "ismaili", "Pakistani and Muslim"),
    "Gujarati Hindu": ("Gujarati Hindu", "gujarati-hindu", "Hindu"),
    "Tamil Hindu": ("Tamil Hindu", "tamil-hindu", "Hindu"),
    "Telugu Hindu": ("Telugu Hindu", "telugu-hindu", "Hindu"),
    "Bengali Hindu": ("Bengali Hindu", "bengali-hindu", "Hindu"),
    "Maharashtrian Hindu": ("Marathi (Maharashtrian Hindu)", "marathi-hindu", "Hindu"),
    "Kerala Hindu": ("Malayali Hindu (Kerala)", "kerala-hindu", "Hindu"),
    "Kannada Hindu": ("Kannada Hindu", "kannada-hindu", "Hindu"),
    "Rajasthani Marwari": ("Rajasthani Marwari", "rajasthani-marwari", "Hindu"),
    "Sindhi Hindu": ("Sindhi Hindu", "sindhi-hindu", "Hindu"),
    "Kashmiri Pandit": ("Kashmiri Pandit", "kashmiri-pandit", "Hindu"),
    "Odia Hindu": ("Odia Hindu", "odia-hindu", "Hindu"),
    "Assamese Hindu": ("Assamese Hindu", "assamese-hindu", "Hindu"),
    "Indo-Caribbean Hindu": ("Indo-Caribbean Hindu", "indo-caribbean-hindu", "Hindu"),
    "Jain": ("Jain", "jain", "Jain, Parsi and Christian"),
    "Parsi": ("Parsi", "parsi", "Jain, Parsi and Christian"),
    "Kerala Christian": ("Kerala Christian", "kerala-christian", "Jain, Parsi and Christian"),
    "Goan Catholic": ("Goan Catholic", "goan-catholic", "Jain, Parsi and Christian"),
}
GROUP_ORDER = ["Punjabi", "Pakistani and Muslim", "Hindu", "Jain, Parsi and Christian"]

# Swift file prefix -> community raw value (file names drop spaces and the "Pakistani" suffix varies).
FILE_TO_COMMUNITY = {
    "SikhPunjabi": "Sikh Punjabi", "HinduPunjabi": "Hindu Punjabi", "PunjabiMuslimPakistani": "Punjabi Muslim",
    "Muhajir": "Muhajir", "SindhiMuslim": "Sindhi Muslim", "Saraiki": "Saraiki", "Pashtun": "Pashtun",
    "Balochi": "Balochi", "NorthIndianMuslim": "North Indian Muslim", "KashmiriMuslim": "Kashmiri Muslim",
    "Ismaili": "Ismaili", "GujaratiHindu": "Gujarati Hindu", "TamilHindu": "Tamil Hindu",
    "TeluguHindu": "Telugu Hindu", "BengaliHindu": "Bengali Hindu", "MaharashtranHindu": "Maharashtrian Hindu",
    "KeralaHindu": "Kerala Hindu", "KannadaHindu": "Kannada Hindu", "RajasthaniMarwari": "Rajasthani Marwari",
    "SindhiHindu": "Sindhi Hindu", "KashmiriPandit": "Kashmiri Pandit", "OdiaHindu": "Odia Hindu",
    "AssameseHindu": "Assamese Hindu", "IndoCaribbeanHindu": "Indo-Caribbean Hindu", "Jain": "Jain",
    "Parsi": "Parsi", "KeralaChristian": "Kerala Christian", "GoanCatholic": "Goan Catholic",
}


# ---------- Swift parsing ----------

def unescape_swift(s):
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            n = s[i + 1]
            if n == "n":
                out.append("\n")
            elif n == "t":
                out.append("\t")
            elif n == "u" and s[i + 2:i + 3] == "{":
                end = s.index("}", i)
                out.append(chr(int(s[i + 3:end], 16)))
                i = end + 1
                continue
            else:
                out.append(n)
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def call_body(src, open_idx):
    """Return the text between the '(' at open_idx and its matching ')', string-aware."""
    depth, i, in_str = 0, open_idx, False
    while i < len(src):
        c = src[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "/" and src[i:i + 2] == "//":
            i = src.index("\n", i)
            continue
        elif c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
            if depth == 0:
                return src[open_idx + 1:i]
        i += 1
    raise ValueError("unbalanced call")


def top_level_args(body):
    """Split 'label: value, label: value' at depth 0, string-aware. Returns {label: raw value}."""
    args, depth, in_str, start, i = {}, 0, False, 0, 0
    parts = []
    while i < len(body):
        c = body[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            parts.append(body[start:i])
            start = i + 1
        i += 1
    parts.append(body[start:])
    for p in parts:
        m = re.match(r"\s*([A-Za-z_]\w*)\s*:\s*(.*)\Z", p, re.S)
        if m:
            args[m.group(1)] = m.group(2).strip()
    return args


def swift_string(raw):
    if raw is None:
        return ""
    m = re.match(r'"((?:[^"\\]|\\.)*)"\Z', raw.strip(), re.S)
    return unescape_swift(m.group(1)) if m else ""


def swift_string_list(raw):
    return [unescape_swift(s) for s in re.findall(r'"((?:[^"\\]|\\.)*)"', raw or "")]


def parse_community_file(path):
    src = open(path, encoding="utf-8").read()
    periods = {m.group(1): unescape_swift(m.group(2)) for m in re.finditer(
        r'static let (\w+)\s*=\s*TimelinePeriod\(\s*title:\s*"((?:[^"\\]|\\.)*)"', src)}
    m = re.search(r"static var \w+Events\s*:\s*\[Event\]", src)
    if not m:
        raise ValueError(f"no events in {path}")
    events_src = src[m.end():]
    events = []
    for em in re.finditer(r"\bEvent\(", events_src):
        body = call_body(events_src, em.end() - 1)
        a = top_level_args(body)
        if "name" not in a:
            continue
        tasks = a.get("tasks", "")
        period_id = (a.get("timelinePeriod") or "").strip().lstrip(".")
        events.append({
            "name": swift_string(a.get("name")),
            "local": swift_string(a.get("localName")),
            "short": swift_string(a.get("shortDescription")),
            "description": swift_string(a.get("ceremonyDescription")),
            "significance": swift_string(a.get("significance")),
            "when": periods.get(period_id, ""),
            "tasks": len(re.findall(r"\bEventTask\(", tasks)),
            "things": len(re.findall(r"itemType:\s*\.thingsNeeded", tasks)),
        })
    # Only top-level Event( calls are ceremonies; EventTask( never matches \bEvent\(.
    return [e for e in events if e["name"] not in NOT_CEREMONIES and e["description"]]


def load_all(app_repo):
    models = os.path.join(app_repo, "LaddoThis", "Models")
    data = {}
    for prefix, raw in FILE_TO_COMMUNITY.items():
        data[raw] = parse_community_file(os.path.join(models, f"{prefix}Defaults.swift"))
    missing = set(COMMUNITIES) - set(data)
    if missing:
        raise SystemExit(f"no data for {missing}")
    return data


# ---------- HTML ----------

e = html.escape


def paras(text):
    return "".join(f"<p>{e(p.strip())}</p>" for p in text.split("\n") if p.strip())


def page(title, description, path, body, jsonld, active):
    url = f"{SITE}{path}"
    ld = "\n".join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False)}</script>' for x in jsonld)
    current = ' aria-current="page"'
    nav = "".join(
        f'<a href="{BASE}{href}"{current if key == active else ""}>{label}</a>'
        for key, href, label in [("guides", "/guides/", "Ceremony guides"), ("support", "/", "Support &amp; Privacy")])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{url}">
<meta name="apple-itunes-app" content="app-id={APP_ID}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="LaddoThis">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{url}">
<link rel="stylesheet" href="{BASE}/assets/site.css">
{ld}
</head>
<body>
<header class="site"><div class="wrap">
  <a class="brand" href="{BASE}/guides/">LaddoThis</a>
  <nav aria-label="Site">{nav}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="site"><div class="wrap">
  <p>LaddoThis is an iPhone app with ready-made ceremony checklists for 28 South Asian communities. <a href="{APP_URL_TRACKED}">Get it on the App Store</a>.</p>
  <p><a href="{BASE}/guides/">All ceremony guides</a> &middot; <a href="{BASE}/">Support &amp; Privacy</a></p>
</div></footer>
</body>
</html>
"""


def app_box(name, n_events, n_tasks, n_things):
    return f"""<aside class="app">
  <h2>Plan every {e(name)} ceremony in one app</h2>
  <p><strong>LaddoThis</strong> turns each of these {n_events} ceremonies into a ready-made checklist: {n_tasks} tasks in all, {n_things} of them things to buy or prepare, split between the bride&rsquo;s side and the groom&rsquo;s side, with reminders for when each one should start. It also has a budget tracker, vendor contacts, a gift tracker and e-card invitations. Free to download on iPhone; one purchase unlocks everything and covers the family through Apple Family Sharing.</p>
  <p><a class="button" href="{APP_URL_TRACKED}">Download LaddoThis on the App Store</a></p>
</aside>"""


def community_page(raw, events):
    name, slug, _ = COMMUNITIES[raw]
    path = f"/guides/{slug}-wedding-ceremonies/"
    names = [ev["name"] for ev in events]
    n_tasks = sum(ev["tasks"] for ev in events)
    n_things = sum(ev["things"] for ev in events)
    seq = ", ".join(names[:-1]) + f" and {names[-1]}" if len(names) > 1 else names[0]
    title = f"{name} Wedding Ceremonies in Order: {names[0]} to {names[-1]}"
    description = (f"Every {name} wedding ceremony in order, from {names[0]} to {names[-1]}: "
                   f"when each happens, what it means and how families do it, with a ready-made checklist for each.")[:300]
    def local(ev):
        return f' <span class="local" lang="und">{e(ev["local"])}</span>' if ev["local"] else ""

    rows = "".join(
        f'<tr><td><a href="#c{i}">{e(ev["name"])}</a>{local(ev)}</td>'
        f'<td>{e(ev["when"])}</td><td>{e(ev["short"])}</td></tr>'
        for i, ev in enumerate(events, 1))
    sections = []
    for i, ev in enumerate(events, 1):
        when = f'<p class="when">{e(ev["when"])}</p>' if ev["when"] else ""
        sig = f'<h3>Why it matters</h3>{paras(ev["significance"])}' if ev["significance"] else ""
        things = f', {ev["things"]} of them things to buy or prepare' if ev["things"] else ""
        checklist = (f'<p class="inapp">In LaddoThis: a {e(ev["name"])} checklist with {ev["tasks"]} tasks{things}.</p>'
                     if ev["tasks"] else "")
        sections.append(f'<section id="c{i}"><h2>{i}. {e(ev["name"])}{local(ev)}</h2>{when}'
                        f'<p class="short">{e(ev["short"])}</p>{paras(ev["description"])}{sig}{checklist}</section>')
    body = f"""<div class="crumbs"><a href="{BASE}/guides/">Ceremony guides</a> &rsaquo; {e(name)}</div>
<h1>{e(name)} wedding ceremonies, in order</h1>
<div class="answer"><p>A {e(name)} wedding usually moves through {len(events)} ceremonies: {e(seq)}. Below is each one in order, when it usually happens and what it means. Customs vary between families and regions, so treat this as the common sequence, not a rule.</p></div>
<h2>At a glance</h2>
<div class="table-scroll"><table><thead><tr><th>Ceremony</th><th>When</th><th>What it is</th></tr></thead><tbody>{rows}</tbody></table></div>
{"".join(sections)}
{app_box(name, len(events), n_tasks, n_things)}
"""
    faq = [
        (f"What is the order of {name} wedding ceremonies?", f"The usual sequence is {seq}. Exact customs vary by family and region."),
        (f"Is there an app with a {name} wedding checklist?",
         f"Yes. LaddoThis is an iPhone app with ready-made checklists for each {name} ceremony ({len(events)} ceremonies, {n_tasks} tasks), plus budget, vendor and gift tracking and e-card invitations. It is free to download, with a one-time purchase to unlock everything."),
    ]
    jsonld = [
        {"@context": "https://schema.org", "@type": "Article", "headline": f"{name} wedding ceremonies, in order",
         "description": description, "datePublished": TODAY, "dateModified": TODAY,
         "author": {"@type": "Organization", "name": "LaddoThis", "url": f"{SITE}/guides/"},
         "publisher": {"@type": "Organization", "name": "LaddoThis", "url": f"{SITE}/guides/"},
         "mainEntityOfPage": f"{SITE}{path}"},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ceremony guides", "item": f"{SITE}/guides/"},
            {"@type": "ListItem", "position": 2, "name": name, "item": f"{SITE}{path}"}]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
    ]
    return path, title, description, page(title, description, path, body, jsonld, "guides")


def hub_page(data):
    path = "/guides/"
    title = "South Asian Wedding Ceremonies by Community: Ceremony Guides and Checklists"
    description = ("Every ceremony, in order, for 28 South Asian wedding traditions: Sikh, Hindu, Pakistani and Indian Muslim, "
                   "Jain, Parsi, Christian and Indo-Caribbean. From LaddoThis, the iPhone app with a checklist for each.")
    total_events = sum(len(v) for v in data.values())
    groups = []
    for g in GROUP_ORDER:
        items = []
        for raw, (name, slug, grp) in COMMUNITIES.items():
            if grp != g:
                continue
            evs = data[raw]
            preview = e(", ".join(ev["name"] for ev in evs[:6])) + (", &hellip;" if len(evs) > 6 else "")
            items.append(f'<li><a href="{BASE}/guides/{slug}-wedding-ceremonies/">{e(name)}</a> '
                         f'<span class="count">{len(evs)} ceremonies</span><br><span class="preview">{preview}</span></li>')
        groups.append(f"<h2>{e(g)}</h2><ul class=\"communities\">{''.join(items)}</ul>")
    body = f"""<h1>Wedding ceremonies by community</h1>
<div class="answer"><p>South Asian weddings are a sequence of ceremonies, and the sequence depends on the family&rsquo;s community: a Sikh Punjabi wedding runs from Roka to Doli, a Pakistani one from Mangni through Dholki, Mayun, Mehndi, Baraat and Nikah to Walima. These guides list every ceremony in order for {len(data)} traditions ({total_events} ceremonies in all), with when each happens and what it means.</p></div>
{''.join(groups)}
<aside class="app">
  <h2>About LaddoThis</h2>
  <p>LaddoThis is an iPhone app for planning South Asian weddings. Pick your community and every ceremony comes as a ready-made checklist, split between the bride&rsquo;s side and the groom&rsquo;s side, with reminders for when to start. It also includes a budget tracker with community-typical categories, vendor contacts, a gift tracker, a photo inspiration board and e-card invitations. Free to download; a one-time purchase unlocks everything and Apple Family Sharing covers up to five family members. Your data stays on your device.</p>
  <p><a class="button" href="{APP_URL_TRACKED}">Download LaddoThis on the App Store</a></p>
</aside>
"""
    jsonld = [
        {"@context": "https://schema.org", "@type": "MobileApplication", "name": "LaddoThis: Indian Weddings",
         "operatingSystem": "iOS", "applicationCategory": "LifestyleApplication", "url": APP_URL,
         "description": "Ceremony-by-ceremony wedding checklists for 28 South Asian communities, with budget, vendor and gift tracking and e-card invitations.",
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}},
        {"@context": "https://schema.org", "@type": "CollectionPage", "name": title, "description": description, "url": f"{SITE}{path}"},
    ]
    return path, title, description, page(title, description, path, body, jsonld, "guides")


def llms_txt(data, guides):
    lines = [
        "# LaddoThis",
        "",
        "> iPhone app for planning South Asian weddings (App Store name: \"LaddoThis: Indian Weddings\"). "
        "Ready-made, ceremony-by-ceremony checklists for 28 communities, with budget, vendor and gift tracking and e-card invitations.",
        "",
        f"- App Store: {APP_URL}",
        f"- Ceremony guides: {SITE}/guides/",
        f"- Support and privacy policy: {SITE}/",
        "",
        "## Facts",
        "- Platform: iPhone (iOS).",
        f"- Communities: {', '.join(COMMUNITIES[r][0] for r in COMMUNITIES)}.",
        f"- {sum(len(v) for v in data.values())} ceremonies in all, each a ready-made checklist with tasks for the bride's side and the groom's side, things to buy, and reminders for when to start.",
        "- Also: budget tracker with community-typical categories, vendor contacts, gift tracker, photo inspiration board, wedding-day countdown and timeline.",
        "- E-card invitations for Save the Date, Jaggo, Sangeet, Mehndi, Anand Karaj, Nikah, Walima, Maticoor, the wedding ceremony and the reception, matched to the community.",
        "- Pricing: free download; one-time purchase unlocks everything; Apple Family Sharing covers up to 5 family members. No subscriptions, no ads; data stays on the device.",
        "",
        "## Ceremony guides",
    ]
    for path, title, description in guides:
        lines.append(f"- [{title}]({SITE}{path}): {description}")
    return "\n".join(lines) + "\n"


def sitemap(paths):
    urls = "".join(f"<url><loc>{SITE}{p}</loc><lastmod>{TODAY}</lastmod></url>\n" for p in paths)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n'


def main():
    app_repo = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/laddo-this")
    site = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data = load_all(app_repo)
    guides = []
    for raw in COMMUNITIES:
        path, title, description, doc = community_page(raw, data[raw])
        out = os.path.join(site, path.strip("/"), "index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "w", encoding="utf-8").write(doc)
        guides.append((path, title, description))
    hub = hub_page(data)
    os.makedirs(os.path.join(site, "guides"), exist_ok=True)
    open(os.path.join(site, "guides", "index.html"), "w", encoding="utf-8").write(hub[3])
    open(os.path.join(site, "llms.txt"), "w", encoding="utf-8").write(llms_txt(data, guides))
    open(os.path.join(site, "sitemap.xml"), "w", encoding="utf-8").write(sitemap(["/", "/guides/"] + [g[0] for g in guides]))
    print(f"{len(guides)} guides, {sum(len(v) for v in data.values())} ceremonies")


if __name__ == "__main__":
    main()
