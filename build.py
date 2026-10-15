"""Build the profile README from profile.json, in a dark and a light palette that GitHub switches by theme.

    uv run --no-project --with pillow python build.py

Everything follows the design system of Dundy's export (JetBrains Mono; cards with 1px borders; one orange accent):
the contributions cards, the in-progress strip, and the eight project cards, whose artwork is cut from the export's
covers/*.png. The page is laid out once in HTML; headless Chrome screenshots it at 2x in each palette, and the page
reports where its bands and columns are, so each PR line and each project card becomes its own linked image.

In the README every image is a <picture> (GitHub wraps it in <themed-picture>, so it follows the GitHub theme setting)
set inline, edge to edge, with align="top": GitHub strips style and bgcolor and pads floated images, and each line
of inline images gets a 24px strut, so no slice may be shorter than ~120px at 2x or phones show a seam.
"""
import base64, html, io, json, pathlib, re, subprocess, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
IMG = ROOT / "img"
USER = "dundysm"
RAW = f"https://raw.githubusercontent.com/{USER}/{USER}/main/"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
FONTS = "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=block"
W = 815            # css px of the contributions panel; the export is 1630px wide at 2x
CARD_W, CARD_H = 207, 386
SCALE = 2
MIN_BAND = 60      # css px; 120px at 2x stays above GitHub's 24px line strut down to phone width
MERGED = f"https://github.com/search?q=author%3A{USER}+is%3Apr+is%3Amerged+-user%3A{USER}&type=pullrequests"
OPEN = f"https://github.com/search?q=author%3A{USER}+is%3Apr+is%3Aopen+-user%3A{USER}&type=pullrequests"
PR_ICON = ('<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">'
           '<circle cx="4.5" cy="3.5" r="1.75"/><circle cx="4.5" cy="12.5" r="1.75"/><circle cx="11.5" cy="9" r="1.75"/>'
           '<path d="M4.5 5.25v5.5M4.5 5.25c0 2.6 2.4 3.75 5.25 3.75"/></svg>')

# dark = the export's palette on GitHub's dark page; light = GitHub's light theme greys with a deeper orange for contrast
THEMES = {
    "dark": dict(page="#0d1117", card="#10141b", border="#1e242e", sep="#1a2029", ink="#e6edf3", muted="#7d8590",
                 desc="#adbac7", accent="#f2c94c", tile="#29303a", pdesc="#8b949e", pill="#161c25", pillb="#262e3a",
                 pillt="#adbac7", artring="transparent"),
    "light": dict(page="#ffffff", card="#f6f8fa", border="#d1d9e0", sep="#e1e6eb", ink="#1f2328", muted="#59636e",
                  desc="#424a53", accent="#a37a00", tile="#d1d9e0", pdesc="#59636e", pill="#ffffff", pillb="#d1d9e0",
                  pillt="#424a53", artring="#d1d9e0"),
}

cfg = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))


def esc(s):
    return html.escape(s, quote=True)


def logo(org):
    """GitHub org avatar, cached; it is only ever baked into an image."""
    p = CACHE / "logos" / f"{org}.png"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(f"https://github.com/{org}.png?size=256", headers={"User-Agent": "dundysm-profile-build"})
        p.write_bytes(urllib.request.urlopen(req, timeout=30).read())
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


def art(path):
    """The artwork panel of an export card: 181x112.5 css at (13, 13), i.e. png (26..388, 26..251)."""
    from PIL import Image
    buf = io.BytesIO()
    Image.open(ROOT / path).convert("RGB").crop((26, 26, 388, 251)).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def tile(org, cls="tile"):
    return f'<span class="{cls}"><img src="{logo(org)}"></span>'


def band(inner, links, alts, cls="", cols=False):
    return (f"<div class=\"band {cls}\"{' data-cols' if cols else ''} data-links='{esc(json.dumps(links))}' "
            f"data-alts='{esc(json.dumps(alts))}'>{inner}</div>")


def item(it, first):
    org, name = it["repo"].split("/")
    prs = it["prs"]
    more = f'<span class="more">+{len(prs) - 1}</span>' if len(prs) > 1 else ""
    return (f'<div class="it{" first" if first else ""}">{tile(org)}<div class="tx">'
            f'<div class="ln"><span class="org">{esc(org.lower())}</span><span class="sl"> / </span>'
            f'<span class="rp">{esc(name.lower())}</span><span class="pr">{PR_ICON}#{prs[0]}{more}</span></div>'
            f'<div class="ds">{esc(it["desc"])}</div></div></div>')


def head(area):
    orgs = list(dict.fromkeys(it["repo"].split("/")[0] for it in area["items"]))
    stack = "".join(tile(o, "st") for o in orgs)
    return f'<div class="hd"><span class="mk"></span><span class="ti">{esc(area["label"])}</span><span class="stk">{stack}</span></div>'


def project(p):
    pills = "".join(f"<span>{esc(t)}</span>" for t in p["tags"])
    return (f'<div class="pc"><div class="fr"></div><img class="art" src="{art(p["art"])}">'
            f'<div class="ptx"><div class="pt">{esc(p["title"])}</div><div class="pd">{esc(p["desc"])}</div></div>'
            f'<div class="pp">{pills}</div></div>')


def page(theme, cards_only=False):
    """The whole panel; cards_only renders just the project cards at the export's native size, for checking."""
    out = []
    for r, (a, b) in enumerate([] if cards_only else cfg["rows"]):
        n = max(len(a["items"]), len(b["items"]))
        for k in range(n):
            # the card header rides on the first slice and the card foot on the last, so no slice is too short
            cells, links, alts = "", [], []
            for x in (a, b):
                cls = "cell" + (" first" if k == 0 else "") + (" last" if k == n - 1 else "")
                body = head(x) if k == 0 else ""
                if k < len(x["items"]):
                    it = x["items"][k]
                    body += item(it, k == 0)
                    links.append(f"https://github.com/{it['repo']}/pull/{it['prs'][0]}")
                    alts.append(f"{it['repo']}#{it['prs'][0]}: {it['desc']}")
                else:
                    links.append(MERGED); alts.append(x["label"])
                cells += f'<div class="{cls}">{body}</div>'
            label = '<div class="lab"><span>open source contributions</span></div>' if (r == 0 and k == 0) else ""
            gap = " gap" if k == n - 1 else ""
            out.append(band(f'{label}<div class="pair" data-cols>{cells}</div>', links, alts, "rowband" + gap))

    tiles = "".join(tile(o, "rt") for o in cfg["review_orgs"])
    if not cards_only: out.append(band(f'<div class="pg"><div class="hd2"><span class="mk"></span><span class="ti2">in progress</span></div>'
                    f'<div class="rts">{tiles}</div></div><div class="lab built"><span>built</span></div>',
                    [OPEN], ["in progress: open prs upstream; built"], "progress"))

    projects = cfg["projects"]
    for r in range(0, len(projects), 4):
        row = projects[r:r + 4]
        out.append(band("".join(project(p) for p in row), [p["href"] for p in row], [p["alt"] for p in row], "prow", cols=True))

    vars_ = ";".join(f"--{k}:{v}" for k, v in THEMES[theme].items())
    width, zoom = (4 * CARD_W, 1) if cards_only else (W, W / (4 * CARD_W))
    css = f"""
:root{{{vars_}}}
html,body{{margin:0;background:var(--page);color:var(--ink);font-family:'JetBrains Mono',monospace}}
#panel{{width:{width}px}}
.lab{{display:flex;gap:17px;height:31px;align-items:flex-start;font-size:12px;line-height:14px;letter-spacing:.12em;color:var(--accent)}}
.lab:after{{content:"";flex:1;height:1px;background:var(--border);margin-top:7px}}
.lab.built{{height:auto;margin-top:16px;padding-bottom:6px}}
.pair{{display:grid;grid-template-columns:1fr 1fr;column-gap:13px}}
.gap{{padding-bottom:14px}}
.cell{{background:var(--card);border-left:1px solid var(--border);border-right:1px solid var(--border);padding:0 20px}}
.cell.first{{border-top:1px solid var(--border);border-radius:12px 12px 0 0}}
.cell.last{{border-bottom:1px solid var(--border);border-radius:0 0 12px 12px;padding-bottom:4px}}
.hd{{display:flex;align-items:center;height:50px;border-bottom:1px solid var(--border)}}
.mk{{width:3px;height:14px;border-radius:2px;margin-right:12px;flex:none;background:var(--accent)}}
.ti{{font-weight:700;font-size:14.5px;line-height:20px}}
.stk{{margin-left:auto;display:flex}}
.st{{width:18px;height:18px;border-radius:5px;overflow:hidden;background:#fff;box-shadow:0 0 0 1.5px var(--card);margin-left:-4px;display:block}}
.st:first-child{{margin-left:0}}
.st img,.tile img,.rt img{{width:100%;height:100%;object-fit:cover;display:block}}
.it{{display:flex;gap:9.5px;padding:10px 0 14px;border-top:1px solid var(--sep)}}
.it.first{{border-top:0}}
.tile{{width:34px;height:34px;border-radius:8px;border:1px solid var(--tile);overflow:hidden;background:#fff;flex:none;box-sizing:border-box;display:block}}
.tx{{flex:1;min-width:0}}
.ln{{display:flex;align-items:center;font-size:11px;line-height:16px;margin-top:3px;white-space:nowrap}}
.org,.sl,.more{{color:var(--muted)}} .sl{{white-space:pre}}
.rp{{font-weight:600}}
.pr{{margin-left:auto;display:flex;align-items:center;gap:6px;color:var(--accent)}}
.more{{margin-left:2px}}
.ds{{font-size:13px;line-height:19px;color:var(--desc);margin-top:4px;text-wrap:pretty}}
.pg{{background:var(--card);border:1px solid var(--border);border-radius:12px;height:100px;box-sizing:border-box;padding:17px 22px 0}}
.hd2{{display:flex;align-items:center;height:20px}}
.ti2{{font-weight:700;font-size:16px;line-height:20px}}
.rts{{display:flex;gap:9px;margin-top:10px}}
.rt{{width:35px;height:35px;border-radius:8px;border:1px solid var(--tile);overflow:hidden;background:#fff;box-sizing:border-box;display:block}}
.prow{{display:flex;width:{4 * CARD_W}px;zoom:{zoom}}}
.pc{{position:relative;width:{CARD_W}px;height:{CARD_H}px;flex:none}}
.fr{{position:absolute;left:6px;top:6px;width:195px;height:375px;box-sizing:border-box;border:1px solid var(--border);border-radius:13px;background:var(--card)}}
.art{{position:absolute;left:13px;top:13px;width:181px;height:112.5px;border-radius:7px;box-shadow:0 0 0 1px var(--artring)}}
.ptx{{position:absolute;left:21px;top:136.75px;width:166px}}
.pt{{font-weight:700;font-size:13.75px;line-height:18.5px}}
.pd{{font-size:11px;line-height:16.5px;color:var(--pdesc);margin-top:6.05px;text-wrap:pretty}}
.pp{{position:absolute;left:21px;width:166px;bottom:18px;display:flex;flex-wrap:wrap;gap:5px}}
.pp span{{height:18px;line-height:18px;padding:0 8px;border:1px solid var(--pillb);background:var(--pill);border-radius:10px;font-size:10px;color:var(--pillt)}}
"""
    js = """<script>
addEventListener('load', () => document.fonts.ready.then(() => {
  const P = document.getElementById('panel').getBoundingClientRect();
  const bands = [...document.querySelectorAll('.band')].map(b => {
    const r = b.getBoundingClientRect();
    const box = b.hasAttribute('data-cols') ? b : b.querySelector('[data-cols]');
    let cuts = [0, P.width];
    if (box) { const k = [...box.children].map(c => c.getBoundingClientRect());
               cuts = [0, ...k.slice(1).map((c, i) => (k[i].right + c.left) / 2), P.width]; }
    return {y0: r.top, y1: r.bottom, cuts, links: JSON.parse(b.dataset.links), alts: JSON.parse(b.dataset.alts)};
  });
  const pre = document.createElement('pre'); pre.id = 'layout'; pre.style.display = 'none';
  pre.textContent = JSON.stringify({W: P.width, H: P.height, bands}); document.body.appendChild(pre);
}));
</script>"""
    return (f'<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="{FONTS}"><style>{css}</style></head>'
            f'<body><div id="panel">{"".join(out)}</div>{js}</body></html>')


def chrome(src, *args):
    return subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--disable-lcd-text",
                           f"--user-data-dir={CACHE / 'chrome'}", "--virtual-time-budget=8000", *args, src.as_uri()],
                          check=True, capture_output=True, text=True, encoding="utf-8").stdout


def render(theme, cards_only=False):
    from PIL import Image
    src = CACHE / f"panel-{theme}{'-cards' if cards_only else ''}.html"
    src.write_text(page(theme, cards_only), encoding="utf-8")
    w = 4 * CARD_W if cards_only else W
    dom = chrome(src, f"--window-size={w},6000", "--dump-dom")
    layout = json.loads(html.unescape(re.search(r'<pre id="layout"[^>]*>(.*?)</pre>', dom, re.S).group(1)))
    shot = CACHE / f"panel-{theme}{'-cards' if cards_only else ''}.png"
    chrome(src, f"--force-device-scale-factor={SCALE}", f"--window-size={w},{int(layout['H']) + 1}", f"--screenshot={shot}")
    return layout, Image.open(shot).convert("RGB")


def build():
    CACHE.mkdir(exist_ok=True)
    renders = {t: render(t) for t in THEMES}
    layout = renders["dark"][0]
    assert json.dumps(layout) == json.dumps(renders["light"][0]), "the two palettes laid out differently"

    for t in THEMES:
        (IMG / t).mkdir(parents=True, exist_ok=True)
        for old in (IMG / t).glob("*.png"):
            old.unlink()
    for old in IMG.glob("*.png"):
        old.unlink()
    px = lambda v: round(v * SCALE)
    cells = []
    for bi, b in enumerate(layout["bands"]):
        assert b["y1"] - b["y0"] >= MIN_BAND, f"band {bi} is {b['y1'] - b['y0']:.0f}px; GitHub's line strut would show a seam"
        cuts = b["cuts"]
        for ci, (x0, x1) in enumerate(zip(cuts, cuts[1:])):
            name = f"{bi:02d}-{ci}.png"
            box = (px(x0), px(b["y0"]), px(x1), px(b["y1"]))
            for t, (_, full) in renders.items():
                full.crop(box).save(IMG / t / name, optimize=True)
            # width from the crop's own pixel width, so every slice in a band scales to exactly the same height
            pct = "100%" if len(cuts) == 2 else f"{int((box[2] - box[0]) / px(layout['W']) * 100 * 10000) / 10000}%"
            cells.append(f'<a href="{esc(b["links"][ci])}"><picture><source media="(prefers-color-scheme: dark)" '
                         f'srcset="{RAW}img/dark/{name}"><img src="{RAW}img/light/{name}" width="{pct}" align="top" '
                         f'alt="{esc(b["alts"][ci])}"></picture></a>')

    (ROOT / "README.md").write_text("<p>" + "".join(cells) + "</p>\n", encoding="utf-8")
    kb = sum(p.stat().st_size for p in IMG.rglob("*.png")) // 1024
    print(f"README.md: {len(cells)} pictures, {len(layout['bands'])} bands, img/ {kb} KB (both palettes), shortest band "
          f"{min(b['y1'] - b['y0'] for b in layout['bands']):.0f}px css")


def check_cards():
    """Render the project cards in the dark palette at native size and diff them against the export."""
    import numpy as np
    from PIL import Image
    layout, full = render("dark", cards_only=True)
    for i, p in enumerate(cfg["projects"]):
        x0, y0 = (i % 4) * CARD_W * SCALE, (i // 4) * CARD_H * SCALE
        mine = np.asarray(full.crop((x0, y0, x0 + CARD_W * SCALE, y0 + CARD_H * SCALE))).astype(int)
        theirs = np.asarray(Image.open(ROOT / p["art"]).convert("RGB")).astype(int)
        d = np.abs(mine - theirs).max(-1)
        print(f"{p['title']:26s} pixels off by >40: whole card {(d > 40).sum():6d}  text area {(d[255:] > 40).sum():6d}")


if __name__ == "__main__":
    import sys
    check_cards() if "--check-cards" in sys.argv else build()
