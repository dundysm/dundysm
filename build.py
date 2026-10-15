"""Build the profile README from shelf.json: merged upstream work as four area cards, open PRs, own projects.

    uv run --no-project --with pillow python build.py           render img/*.webp and README.md
    uv run --no-project --with pillow python build.py --check   list upstream PRs that shelf.json doesn't cover yet

The whole panel is laid out once as an HTML page (dark, Newsreader + JetBrains Mono, both OFL) and headless Chrome
screenshots it. The page also reports where its bands and columns are, and each cell becomes its own image, so
every PR stays a link (GitHub shows its hovercard). The README sets the images inline, edge to edge, with
align="top": GitHub strips style and bgcolor and pads floated images, so this is what keeps the panel one dark
block in GitHub's light theme too. Titles are written by hand. No totals are printed anywhere, on purpose.
"""
import base64, html, json, mimetypes, pathlib, re, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
IMG = ROOT / "img"
USER = "dundysm"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
FONTS = ("https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500"
         "&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&display=block")
W = 846        # GitHub profile README content width at a 1280px window; images scale with it anyway
SCALE = 2
GOLD = "#d4af37"
MERGED = f"https://github.com/search?q=author%3A{USER}+is%3Apr+is%3Amerged+-user%3A{USER}&type=pullrequests"
OPEN = f"https://github.com/search?q=author%3A{USER}+is%3Apr+is%3Aopen+-user%3A{USER}&type=pullrequests"

shelf = json.loads((ROOT / "shelf.json").read_text(encoding="utf-8"))


def gh_prs(state):
    flag = ["--merged"] if state == "merged" else ["--state", "open"]
    out = subprocess.run(["gh", "search", "prs", "--author", USER, *flag, "--limit", "300",
                          "--json", "repository,number,title,url"], capture_output=True, text=True, check=True).stdout
    return [p for p in json.loads(out) if not p["repository"]["nameWithOwner"].lower().startswith(USER + "/")]


def data_uri(path):
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def logo(org):
    """GitHub org avatar, cached; it is only ever baked into an image."""
    p = CACHE / "logos" / f"{org}.png"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(f"https://github.com/{org}.png?size=256", headers={"User-Agent": "dundysm-profile-build"})
        p.write_bytes(urllib.request.urlopen(req, timeout=30).read())
    return data_uri(p)


def esc(s):
    return html.escape(s, quote=True)


def lg(org, size):
    return f'<div class="l" style="width:{size}px;height:{size}px"><img src="{logo(org)}"></div>'


def pr_link(it):
    prs = it["prs"]
    return (f"https://github.com/{it['repo']}/pull/{prs[0]}" if len(prs) == 1 else
            f"https://github.com/{it['repo']}/pulls?q=is%3Apr+author%3A{USER}+is%3Amerged")


def band(inner, links, alts, cls="", cols=False):
    """One horizontal band of the panel. With cols, each child of the band is its own image and link."""
    return (f"<div class=\"band {cls}\"{' data-cols' if cols else ''} data-links='{esc(json.dumps(links))}' "
            f"data-alts='{esc(json.dumps(alts))}'>{inner}</div>")


def page():
    out = [band('<div class="sec">merged upstream</div>', [MERGED], ["merged upstream"], "top")]
    areas = shelf["areas"]
    for a, b in zip(areas[0::2], areas[1::2]):
        n = max(len(a["items"]), len(b["items"]))
        for k in range(n):
            # the header rides on the first row and the card's foot on the last: GitHub gives every line of inline
            # images a 24px strut, so a slice shorter than that would leave a page-coloured seam under it
            cells, links, alts = "", [], []
            for x in (a, b):
                cls = "cell" + (" first" if k == 0 else "") + (" last" if k == n - 1 else "")
                head = (f'<div class="ch"><span class="sw" style="background:{x["accent"]}"></span>{esc(x["label"])}</div>'
                        if k == 0 else "")
                if k < len(x["items"]):
                    it = x["items"][k]
                    body = (f'<div class="it">{lg(it["repo"].split("/")[0], 20)}<div>'
                            f'<div class="rn">{esc(it["repo"])}</div><div class="fx">{esc(it["title"])}</div></div></div>')
                    links.append(pr_link(it)); alts.append(f"{it['repo']}: {it['title']}")
                else:
                    body = ""
                    links.append(MERGED); alts.append(x["label"])
                cells += f'<div class="{cls}">{head}{body}</div>'
            out.append(band(cells, links, alts, "pair" + (" end" if k == n - 1 else ""), cols=True))

    logos = "".join(lg(o, 20) for o in shelf["review_orgs"])
    out.append(band(f'<div class="rv"><span>in review</span><span class="lgs">{logos}</span></div>', [OPEN], ["more prs, in review upstream"], "review"))

    cards = "".join(
        f'<div class="b"><div class="th"><img src="{data_uri(ROOT / e["art"])}" style="object-position:{e["pos"]}"></div>'
        f'<div class="bn">{esc(e["name"])}</div><div class="bs">{esc(e["sub"])}</div></div>' for e in shelf["built"])
    out.append(band(f'<div class="sec">built</div><div class="bg" data-cols>{cards}</div>',
                    [f"https://github.com/{e['repo']}" for e in shelf["built"]],
                    [f"{e['repo']}: {e['sub']}" for e in shelf["built"]], "built"))

    css = f"""
html,body{{margin:0;background:#0d1117;color:#f4f1eb}}
#panel{{width:{W}px}}
.band{{padding:0 36px}}
.l{{border-radius:50%;background:#fff;overflow:hidden;display:flex;align-items:center;justify-content:center;flex:none}}
.l img{{width:78%;height:78%;object-fit:contain}}
.sec{{font-family:'JetBrains Mono',monospace;font-size:12px;letter-spacing:.14em;color:{GOLD}}}
.top{{padding-top:34px;padding-bottom:24px}}
.pair{{display:grid;grid-template-columns:1fr 1fr;column-gap:14px}}
.cell{{border-left:1px solid rgba(244,241,235,.09);border-right:1px solid rgba(244,241,235,.09);background:rgba(255,255,255,.018);padding:0 20px}}
.cell.first{{border-top:1px solid rgba(244,241,235,.09);border-radius:8px 8px 0 0}}
.cell.last{{border-bottom:1px solid rgba(244,241,235,.09);border-radius:0 0 8px 8px;padding-bottom:8px}}
.ch{{padding-top:18px;padding-bottom:10px;font-family:Newsreader,serif;font-size:22px;display:flex;align-items:center;gap:10px}}
.sw{{width:18px;height:3px;border-radius:2px}}
.end{{padding-bottom:14px}}
.it{{display:flex;gap:12px;align-items:flex-start;padding:11px 0;min-height:50px;border-top:1px solid rgba(244,241,235,.06)}}
.it .l{{margin-top:2px}}
.rn{{font-family:'JetBrains Mono',monospace;font-size:11.5px;color:rgba(244,241,235,.9)}}
.fx{{font-family:Newsreader,serif;font-size:15px;color:rgba(244,241,235,.66);margin-top:2px;line-height:1.3}}
.review{{padding-top:26px;padding-bottom:26px}}
.rv{{display:flex;align-items:center;gap:16px;font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.12em;color:{GOLD}}}
.lgs{{display:flex;gap:6px}}
.built{{padding-top:12px;padding-bottom:30px}}
.built .sec{{margin-bottom:14px}}
.bg{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}
.th{{aspect-ratio:16/10;border-radius:6px;overflow:hidden;box-shadow:0 0 0 1px rgba(255,255,255,.08)}}
.th img{{width:100%;height:100%;object-fit:cover;display:block}}
.bn{{font-family:Newsreader,serif;font-size:19px;margin-top:9px}}
.bs{{font-family:'JetBrains Mono',monospace;font-size:11px;color:rgba(244,241,235,.5);margin-top:3px;line-height:1.35}}
"""
    js = """<script>
addEventListener('load', () => {
  for (const im of document.querySelectorAll('.l img')) {   // logo circle takes the avatar's own corner colour
    const k = document.createElement('canvas'); k.width = k.height = 64; const g = k.getContext('2d');
    g.drawImage(im, 0, 0, 64, 64); const [r, gg, b, a] = g.getImageData(2, 2, 1, 1).data;
    if (a > 200) im.parentElement.style.background = `rgb(${r},${gg},${b})`;
  }
  document.fonts.ready.then(() => {                          // report band rows and column cuts for slicing
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
  });
});
</script>"""
    return (f'<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="{FONTS}"><style>{css}</style></head>'
            f'<body><div id="panel">{"".join(out)}</div>{js}</body></html>')


def chrome(src, *args):
    return subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={CACHE / 'chrome'}",
                           "--virtual-time-budget=8000", *args, src.as_uri()], check=True, capture_output=True, text=True,
                          encoding="utf-8").stdout


def check():
    have = {(it["repo"], n) for a in shelf["areas"] for it in a["items"] for n in it["prs"]}
    new = [p for p in gh_prs("merged") if (p["repository"]["nameWithOwner"], p["number"]) not in have]
    for p in new:
        print(f"merged, not in shelf.json: {p['repository']['nameWithOwner']}#{p['number']} {p['title']}")
    orgs = {p["repository"]["nameWithOwner"].split("/")[0] for p in gh_prs("open")}
    missing = sorted(orgs - set(shelf["review_orgs"]))
    if missing:
        print("open-PR orgs without a logo in the review row:", ", ".join(missing))
    if not new and not missing:
        print("shelf.json is up to date")


def build():
    from PIL import Image
    CACHE.mkdir(exist_ok=True)
    src = CACHE / "panel.html"
    src.write_text(page(), encoding="utf-8")
    dom = chrome(src, "--window-size=%d,3000" % W, "--dump-dom")
    layout = json.loads(html.unescape(re.search(r'<pre id="layout"[^>]*>(.*?)</pre>', dom, re.S).group(1)))
    shot = CACHE / "panel.png"
    chrome(src, f"--force-device-scale-factor={SCALE}", f"--window-size={W},{int(layout['H']) + 1}", f"--screenshot={shot}")
    full = Image.open(shot).convert("RGB")

    for old in IMG.glob("*.webp"):
        old.unlink()
    IMG.mkdir(exist_ok=True)
    px = lambda v: round(v * SCALE)
    cells = []
    for bi, b in enumerate(layout["bands"]):
        cuts = b["cuts"]
        for ci, (x0, x1) in enumerate(zip(cuts, cuts[1:])):
            name = f"{bi:02d}-{ci}.webp"
            full.crop((px(x0), px(b["y0"]), px(x1), px(b["y1"]))).save(IMG / name, "WEBP", quality=92, method=6)
            pct = "100%" if len(cuts) == 2 else f"{int((x1 - x0) / layout['W'] * 100 * 1000) / 1000}%"
            cells.append(f'<a href="{esc(b["links"][ci])}"><img src="img/{name}" width="{pct}" align="top" alt="{esc(b["alts"][ci])}"></a>')

    readme = "\n".join(["<!-- generated by build.py from shelf.json; edit those, not this file -->",
                        "<p>" + "".join(cells) + "</p>", ""])
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    kb = sum(p.stat().st_size for p in IMG.glob("*.webp")) // 1024
    low = min(b["y1"] - b["y0"] for b in layout["bands"])
    print(f"README.md: {len(cells)} images in {len(layout['bands'])} bands, {kb} KB, shortest band {low:.0f}px")
    assert low >= 72, "a band under 72px shows a seam on phones (GitHub's 24px line strut at ~0.34 scale)"


if __name__ == "__main__":
    check() if "--check" in sys.argv else build()
