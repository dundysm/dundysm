"""Build the profile README: the contributions cards and the in-progress strip from profile.json, followed by the
eight project cards from Dundy's design export (covers/*.png, used as they are).

    uv run --no-project --with pillow python build.py

The cards follow the export's design system (JetBrains Mono, #10141b cards with #1e242e borders on GitHub's #0d1117,
per-area accents) and are laid out once as an HTML page that headless Chrome screenshots at 2x. The page reports
where its bands and columns are, and every PR line becomes its own image linked straight to its PR. The README sets
all images inline, edge to edge, with align="top": GitHub strips style and bgcolor and pads floated images, and every
line of inline images gets a 24px strut, so no slice may be shorter than ~120px at 2x or phones show a seam.
"""
import base64, html, json, pathlib, re, subprocess, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
IMG = ROOT / "img"
USER = "dundysm"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
FONTS = "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=block"
W = 815            # css px; the export is 1630px wide at 2x
SCALE = 2
MIN_BAND = 60      # css px; 120px at 2x stays above GitHub's 24px line strut down to phone width
MERGED = f"https://github.com/search?q=author%3A{USER}+is%3Apr+is%3Amerged+-user%3A{USER}&type=pullrequests"
OPEN = f"https://github.com/search?q=author%3A{USER}+is%3Apr+is%3Aopen+-user%3A{USER}&type=pullrequests"
PR_ICON = ('<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5">'
           '<circle cx="4.5" cy="3.5" r="1.75"/><circle cx="4.5" cy="12.5" r="1.75"/><circle cx="11.5" cy="9" r="1.75"/>'
           '<path d="M4.5 5.25v5.5M4.5 5.25c0 2.6 2.4 3.75 5.25 3.75"/></svg>')

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


def tile(org, cls="tile"):
    return f'<span class="{cls}"><img src="{logo(org)}"></span>'


def band(inner, links, alts, cls="", cols=False):
    return (f"<div class=\"band {cls}\"{' data-cols' if cols else ''} data-links='{esc(json.dumps(links))}' "
            f"data-alts='{esc(json.dumps(alts))}'>{inner}</div>")


def item(it, accent, first):
    org, name = it["repo"].split("/")
    prs = it["prs"]
    more = f'<span class="more">+{len(prs) - 1}</span>' if len(prs) > 1 else ""
    return (f'<div class="it{" first" if first else ""}">{tile(org)}<div class="tx">'
            f'<div class="ln"><span class="org">{esc(org.lower())}</span><span class="sl"> / </span>'
            f'<span class="rp">{esc(name.lower())}</span>'
            f'<span class="pr" style="color:{accent}">{PR_ICON}#{prs[0]}{more}</span></div>'
            f'<div class="ds">{esc(it["desc"])}</div></div></div>')


def head(area):
    orgs = list(dict.fromkeys(it["repo"].split("/")[0] for it in area["items"]))
    stack = "".join(tile(o, "st") for o in orgs)
    return (f'<div class="hd"><span class="mk" style="background:{area["accent"]}"></span>'
            f'<span class="ti">{esc(area["label"])}</span><span class="stk">{stack}</span></div>')


def page():
    out = []
    for r, (a, b) in enumerate(cfg["rows"]):
        n = max(len(a["items"]), len(b["items"]))
        for k in range(n):
            # the card header rides on the first slice and the card foot on the last, so no slice is too short
            cells, links, alts = "", [], []
            for x in (a, b):
                cls = "cell" + (" first" if k == 0 else "") + (" last" if k == n - 1 else "")
                body = head(x) if k == 0 else ""
                if k < len(x["items"]):
                    it = x["items"][k]
                    body += item(it, x["accent"], k == 0)
                    links.append(f"https://github.com/{it['repo']}/pull/{it['prs'][0]}")
                    alts.append(f"{it['repo']}#{it['prs'][0]}: {it['desc']}")
                else:
                    links.append(MERGED); alts.append(x["label"])
                cells += f'<div class="{cls}">{body}</div>'
            label = '<div class="lab"><span>open source contributions</span></div>' if (r == 0 and k == 0) else ""
            gap = " gap" if k == n - 1 else ""
            out.append(band(f'{label}<div class="pair" data-cols>{cells}</div>', links, alts, "rowband" + gap))

    tiles = "".join(tile(o, "rt") for o in cfg["review_orgs"])
    out.append(band(f'<div class="pg"><div class="hd2"><span class="mk" style="background:#eaa16f"></span>'
                    f'<span class="ti2">in progress</span></div><div class="rts">{tiles}</div></div>'
                    f'<div class="lab built"><span>built</span></div>', [OPEN], ["in progress: open prs upstream; built"], "progress"))

    css = f"""
html,body{{margin:0;background:#0d1117;color:#e6edf3;font-family:'JetBrains Mono',monospace}}
#panel{{width:{W}px}}
.lab{{display:flex;gap:17px;height:31px;align-items:flex-start;font-size:12px;line-height:14px;letter-spacing:.12em;color:#eaa16f}}
.lab:after{{content:"";flex:1;height:1px;background:#1e242e;margin-top:7px}}
.lab.built{{height:auto;margin-top:16px;padding-bottom:6px}}
.pair{{display:grid;grid-template-columns:1fr 1fr;column-gap:13px}}
.gap{{padding-bottom:14px}}
.cell{{background:#10141b;border-left:1px solid #1e242e;border-right:1px solid #1e242e;padding:0 20px}}
.cell.first{{border-top:1px solid #1e242e;border-radius:12px 12px 0 0}}
.cell.last{{border-bottom:1px solid #1e242e;border-radius:0 0 12px 12px;padding-bottom:4px}}
.hd{{display:flex;align-items:center;height:50px;border-bottom:1px solid #1e242e}}
.mk{{width:3px;height:14px;border-radius:2px;margin-right:12px;flex:none}}
.ti{{font-weight:700;font-size:14.5px;line-height:20px;color:#e6edf3}}
.stk{{margin-left:auto;display:flex}}
.st{{width:18px;height:18px;border-radius:5px;overflow:hidden;background:#fff;box-shadow:0 0 0 1.5px #10141b;margin-left:-4px;display:block}}
.st:first-child{{margin-left:0}}
.st img,.tile img,.rt img{{width:100%;height:100%;object-fit:cover;display:block}}
.it{{display:flex;gap:9.5px;padding:10px 0 14px;border-top:1px solid #1a2029}}
.it.first{{border-top:0}}
.tile{{width:34px;height:34px;border-radius:8px;border:1px solid #29303a;overflow:hidden;background:#fff;flex:none;box-sizing:border-box;display:block}}
.tx{{flex:1;min-width:0}}
.ln{{display:flex;align-items:center;font-size:11px;line-height:16px;margin-top:3px;white-space:nowrap}}
.org,.sl{{color:#7d8590}} .sl{{white-space:pre}}
.rp{{color:#e6edf3;font-weight:600}}
.pr{{margin-left:auto;display:flex;align-items:center;gap:6px}}
.more{{color:#7d8590;margin-left:2px}}
.ds{{font-size:13px;line-height:19px;color:#adbac7;margin-top:4px}}
.progress{{padding-top:0}}
.pg{{background:#10141b;border:1px solid #1e242e;border-radius:12px;height:100px;box-sizing:border-box;padding:17px 22px 0}}
.hd2{{display:flex;align-items:center;height:20px}}
.ti2{{font-weight:700;font-size:16px;line-height:20px;color:#e6edf3}}
.rts{{display:flex;gap:9px;margin-top:10px}}
.rt{{width:35px;height:35px;border-radius:8px;border:1px solid #23262d;overflow:hidden;background:#fff;box-sizing:border-box;display:block}}
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


def build():
    from PIL import Image
    CACHE.mkdir(exist_ok=True)
    src = CACHE / "panel.html"
    src.write_text(page(), encoding="utf-8")
    dom = chrome(src, f"--window-size={W},4000", "--dump-dom")
    layout = json.loads(html.unescape(re.search(r'<pre id="layout"[^>]*>(.*?)</pre>', dom, re.S).group(1)))
    shot = CACHE / "panel.png"
    chrome(src, f"--force-device-scale-factor={SCALE}", f"--window-size={W},{int(layout['H']) + 1}", f"--screenshot={shot}")
    full = Image.open(shot).convert("RGB")

    IMG.mkdir(exist_ok=True)
    for old in IMG.glob("*.png"):
        old.unlink()
    px = lambda v: round(v * SCALE)
    cells = []
    for bi, b in enumerate(layout["bands"]):
        assert b["y1"] - b["y0"] >= MIN_BAND, f"band {bi} is {b['y1'] - b['y0']:.0f}px; GitHub's line strut would show a seam"
        cuts = b["cuts"]
        for ci, (x0, x1) in enumerate(zip(cuts, cuts[1:])):
            name = f"{bi:02d}-{ci}.png"
            full.crop((px(x0), px(b["y0"]), px(x1), px(b["y1"]))).save(IMG / name, optimize=True)
            pct = "100%" if len(cuts) == 2 else f"{int((x1 - x0) / layout['W'] * 100 * 1000) / 1000}%"
            cells.append(f'<a href="{esc(b["links"][ci])}"><img src="img/{name}" width="{pct}" align="top" alt="{esc(b["alts"][ci])}"></a>')
    for p in cfg["projects"]:
        cells.append(f'<a href="{esc(p["href"])}"><img src="{p["img"]}" width="25%" align="top" alt="{esc(p["alt"])}"></a>')

    (ROOT / "README.md").write_text("<p>" + "".join(cells) + "</p>\n", encoding="utf-8")
    kb = sum(p.stat().st_size for p in IMG.glob("*.png")) // 1024
    print(f"README.md: {len(cells)} images, {len(layout['bands'])} bands, img/ {kb} KB, shortest band "
          f"{min(b['y1'] - b['y0'] for b in layout['bands']):.0f}px css")


if __name__ == "__main__":
    build()
