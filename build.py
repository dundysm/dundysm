"""Build the profile README: a dark bookshelf. One cover per upstream repo with merged work, one for open PRs,
one per own project, plus a header, a section label and a footer.

    uv run --with pillow build.py           render covers/*.webp and README.md from shelf.json
    uv run --with pillow build.py --check   list upstream PRs (merged or open) that shelf.json doesn't cover yet

Titles are written by hand in shelf.json. Every image carries its own dark background and the README floats them
edge to edge (align="left", widths summing to 100%), so the shelf reads as one dark panel in GitHub's light theme
too; GitHub strips style and bgcolor, but keeps align and <br clear>. No totals are printed anywhere on purpose.
Images are rendered by headless Chrome (fonts: Newsreader and JetBrains Mono from Google Fonts, both OFL).
"""
import base64, html, json, mimetypes, pathlib, re, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
COVERS = ROOT / "covers"
USER = "dundysm"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
FONTS = ("https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500"
         "&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&display=block")
INK = "#f4f1eb"
PANEL = "#0d1117"          # GitHub's dark page background, so the panel disappears into it in dark mode
GOLD = "#d4af37"
TILE_W, TILE_H = 440, 664  # one cover (400x600) plus its gutter and a strip of shelf
ROW_W = 4 * TILE_W

shelf = json.loads((ROOT / "shelf.json").read_text(encoding="utf-8"))
DOM = shelf["domains"]


def gh_prs(state):
    flag = ["--merged"] if state == "merged" else ["--state", "open"]
    out = subprocess.run(["gh", "search", "prs", "--author", USER, *flag, "--limit", "300",
                          "--json", "repository,number,title,url"], capture_output=True, text=True, check=True).stdout
    return [p for p in json.loads(out) if not p["repository"]["nameWithOwner"].lower().startswith(USER + "/")]


def data_uri(path):
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def logo(org):
    """GitHub org avatar, cached; it is only ever baked into a cover."""
    p = CACHE / "logos" / f"{org}.png"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(f"https://github.com/{org}.png?size=256", headers={"User-Agent": "dundysm-profile-build"})
        p.write_bytes(urllib.request.urlopen(req, timeout=30).read())
    return data_uri(p)


def esc(s):
    return html.escape(s, quote=True)


BASE_CSS = f"""
html,body{{margin:0;background:{PANEL};color:{INK};font-family:'JetBrains Mono',monospace;overflow:hidden}}
.serif{{font-family:Newsreader,serif}}
"""

# logos sit inside a circle on their own background colour, sampled from the avatar's corner once it has loaded
LOGO_JS = """<script>
addEventListener('load', () => { for (const im of document.querySelectorAll('.l img')) {
  const k = document.createElement('canvas'); k.width = k.height = 64; const g = k.getContext('2d');
  g.drawImage(im, 0, 0, 64, 64); const [r, gg, b, a] = g.getImageData(2, 2, 1, 1).data;
  if (a > 200) im.parentElement.style.background = `rgb(${r},${gg},${b})`;
} });
</script>"""


def cover_page(inner, bg, accent, extra=""):
    css = f"""{BASE_CSS}
.tile{{position:relative;width:{TILE_W}px;height:{TILE_H}px}}
.plank{{position:absolute;left:0;right:0;top:624px;height:14px;background:linear-gradient(180deg,#252b34,#171c23);
   box-shadow:inset 0 1px 0 rgba(255,255,255,.10)}}
.plank:after{{content:"";position:absolute;left:0;right:0;top:14px;height:20px;background:linear-gradient(180deg,rgba(0,0,0,.45),transparent)}}
.drop{{position:absolute;left:28px;right:12px;top:612px;height:16px;border-radius:50%;background:rgba(0,0,0,.6);filter:blur(7px)}}
.c{{position:absolute;left:20px;top:24px;width:400px;height:600px;box-sizing:border-box;overflow:hidden;border-radius:3px 7px 4px 3px;
   background:radial-gradient(130% 70% at 25% 0%,rgba(255,255,255,.075),transparent 62%),radial-gradient(90% 60% at 80% 110%,rgba(0,0,0,.28),transparent 70%),{bg};
   box-shadow:inset 0 0 0 1px rgba(255,255,255,.07);padding:38px 32px 30px 54px}}
.c:before{{content:"";position:absolute;z-index:3;left:0;top:0;bottom:0;width:22px;
   background:linear-gradient(90deg,rgba(0,0,0,.42),rgba(255,255,255,.08) 55%,rgba(0,0,0,.3))}}
.c:after{{content:"";position:absolute;z-index:3;left:22px;top:0;bottom:0;width:1px;background:rgba(0,0,0,.4);box-shadow:1px 0 0 rgba(255,255,255,.06)}}
.top{{position:relative;z-index:2;display:flex;justify-content:space-between;font-size:15px;letter-spacing:.12em;color:{accent}}}
.top .n{{color:rgba(244,241,235,.45);letter-spacing:.06em}}
.rule{{position:relative;z-index:2;width:36px;height:2px;background:{accent};margin-top:14px}}
.pin{{width:100px;height:100px;margin:34px auto 0;padding:7px;border-radius:50%;border:1.5px solid {accent};box-shadow:0 14px 34px rgba(0,0,0,.35)}}
.l{{border-radius:50%;background:#fff;overflow:hidden;display:flex;align-items:center;justify-content:center}}
.l img{{width:78%;height:78%;object-fit:contain}}
.pin .l{{width:100px;height:100px}}
.t{{font-family:Newsreader,serif;font-weight:400;font-size:38px;line-height:1.1;letter-spacing:-.005em;margin-top:30px;font-variation-settings:'opsz' 48}}
.bot{{position:absolute;z-index:2;left:54px;right:32px;bottom:30px}}
.hr{{height:1px;background:rgba(244,241,235,.14);margin-bottom:16px}}
.org{{font-size:16px;color:rgba(244,241,235,.55)}}
.name{{font-size:22px;font-weight:500;margin-top:3px;word-break:break-all}}
.meta{{display:flex;justify-content:space-between;margin-top:14px;font-size:15px;letter-spacing:.02em}}
.meta .m{{color:{accent}}} .meta .d{{color:rgba(244,241,235,.45)}}
.grid{{display:grid;grid-template-columns:repeat(4,56px);gap:12px;justify-content:center;margin-top:34px}}
.grid .l{{width:56px;height:56px;box-shadow:0 0 0 1.5px rgba(244,241,235,.16),0 8px 18px rgba(0,0,0,.3)}}
.art{{position:absolute;z-index:1;left:23px;right:0;top:0;height:350px}}
.art img{{width:100%;height:100%;object-fit:cover;display:block}}
.art:after{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.5),transparent 26%,transparent 42%,{bg} 98%)}}
.built .top{{color:{INK};text-shadow:0 1px 6px rgba(0,0,0,.6)}} .built .rule{{box-shadow:0 1px 6px rgba(0,0,0,.5)}}
.built .t{{position:absolute;z-index:2;left:54px;right:32px;top:318px;margin:0;font-size:44px}}
.sub{{position:absolute;z-index:2;left:54px;right:32px;top:380px;font-family:Newsreader,serif;font-style:italic;font-size:21px;line-height:1.25;
   color:rgba(244,241,235,.72);font-variation-settings:'opsz' 20}}
{extra}"""
    return (f'<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="{FONTS}"><style>{css}</style></head>'
            f'<body><div class="tile"><div class="plank"></div><div class="drop"></div>{inner}</div>{LOGO_JS}</body></html>')


def strip_page(inner, height, css):
    return (f'<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="{FONTS}"><style>{BASE_CSS}'
            f'.s{{position:relative;width:{ROW_W}px;height:{height}px;box-sizing:border-box;padding:0 44px}}{css}</style></head>'
            f'<body><div class="s">{inner}</div></body></html>')


def bottom(org, name, left, right=""):
    return (f'<div class="bot"><div class="hr"></div><div class="org">{esc(org)}/</div><div class="name">{esc(name)}</div>'
            f'<div class="meta"><span class="m">{esc(left)}</span><span class="d">{esc(right)}</span></div></div>')


def merged_cover(e):
    d = DOM[e["domain"]]; org, name = e["repo"].split("/")
    prs = e["prs"]
    left = f"merged · #{prs[0]}" if len(prs) == 1 else f"{len(prs)} merged · #{prs[0]} +{len(prs) - 1}"
    inner = (f'<div class="c"><div class="top"><span>{d["label"]}</span><span class="n">{esc(e["date"])}</span></div><div class="rule"></div>'
             f'<div class="pin"><div class="l"><img src="{logo(org)}"></div></div><div class="t">{esc(e["title"])}</div>'
             + bottom(org, name, left) + "</div>")
    return cover_page(inner, d["bg"], d["accent"])


def review_cover():
    d = DOM["review"]
    imgs = "".join(f'<div class="l"><img src="{logo(o)}"></div>' for o in shelf["review_orgs"][:16])
    inner = (f'<div class="c"><div class="top"><span>{d["label"]}</span><span class="n">open</span></div><div class="rule"></div>'
             f'<div class="grid">{imgs}</div><div class="t" style="margin-top:34px">{esc(shelf["review_title"])}</div>'
             f'<div class="bot"><div class="hr"></div><div class="meta" style="margin-top:0"><span class="m">open prs, upstream</span>'
             f'<span class="d"></span></div></div></div>')
    return cover_page(inner, d["bg"], d["accent"])


def built_cover(e):
    d = DOM["built"]; org, name = e["repo"].split("/")
    inner = (f'<div class="c built"><div class="art"><img src="{data_uri(ROOT / e["art"])}" style="object-position:{e["pos"]}"></div>'
             f'<div class="top"><span>{d["label"]}</span><span class="n"></span></div><div class="rule"></div>'
             f'<div class="t">{esc(e["name"])}</div><div class="sub">{esc(e["sub"])}</div>'
             + bottom(org, name, e["tags"]) + "</div>")
    return cover_page(inner, d["bg"], d["accent"])


LABEL_CSS = f""".lab{{position:absolute;left:64px;bottom:22px;font-size:26px;letter-spacing:.12em;color:{GOLD}}}
.lab:after{{content:"";display:block;width:44px;height:2px;background:{GOLD};margin-top:16px}}"""


def header_page():
    h = shelf["header"]
    inner = (f'<div class="nm serif">{esc(h["name"])}</div><div class="tg">{esc(h["tagline"])}</div>'
             f'<div class="in serif">{esc(h["intro"])}</div><div class="lab">merged upstream</div>')
    css = f"""{LABEL_CSS}
.nm{{position:absolute;left:62px;top:70px;font-size:80px;line-height:1;letter-spacing:-.01em;font-variation-settings:'opsz' 72}}
.tg{{position:absolute;left:66px;top:172px;font-size:26px;letter-spacing:.04em;color:rgba(244,241,235,.55)}}
.in{{position:absolute;left:64px;top:232px;width:1240px;font-size:36px;line-height:1.3;color:rgba(244,241,235,.82);font-variation-settings:'opsz' 30}}"""
    return strip_page(inner, 420, css)


def label_page(text):
    return strip_page(f'<div class="lab">{esc(text)}</div>', 150, LABEL_CSS)


def footer_page(text, width):
    css = f""".s{{width:{width}px!important;padding:0!important}}
.f{{position:absolute;left:0;right:0;top:46px;text-align:center;font-size:26px;letter-spacing:.04em;color:rgba(244,241,235,.62)}}
.f b{{font-weight:400;color:{GOLD}}}"""
    return strip_page(f'<div class="f">{text}</div>', 140, css)


def render(html_text, out, w, h, scale):
    """HTML -> headless Chrome PNG -> lossy WebP. Opaque, so tiles butt together without seams."""
    from PIL import Image
    out_png = CACHE / "png" / (out.stem + ".png")
    src = CACHE / "html" / (out.stem + ".html")
    for p in (out_png, src, out):
        p.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(html_text, encoding="utf-8")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={CACHE / 'chrome'}",
                    f"--force-device-scale-factor={scale}", f"--window-size={w},{h}",
                    "--virtual-time-budget=8000", f"--screenshot={out_png}", src.as_uri()],
                   check=True, capture_output=True)
    Image.open(out_png).convert("RGB").save(out, "WEBP", quality=90, method=6)
    print("  ", out.relative_to(ROOT), f"{out.stat().st_size // 1024} KB")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def tile(href, src, alt, width):
    return f'<a href="{esc(href)}"><img src="{src}" width="{width}" align="left" alt="{esc(alt)}"></a>'


def check():
    have = {(e["repo"], n) for e in shelf["merged"] for n in e["prs"]}
    new = [p for p in gh_prs("merged") if (p["repository"]["nameWithOwner"], p["number"]) not in have]
    for p in new:
        print(f"merged, not on the shelf: {p['repository']['nameWithOwner']}#{p['number']} {p['title']}")
    orgs = {p["repository"]["nameWithOwner"].split("/")[0] for p in gh_prs("open")}
    missing = sorted(orgs - set(shelf["review_orgs"]))
    if missing:
        print("open-PR orgs without a logo on the review cover:", ", ".join(missing))
    if not new and not missing:
        print("shelf is up to date")


def build():
    for old in [*COVERS.glob("*.png"), *COVERS.glob("*.webp")]:
        old.unlink()
    C = lambda name: COVERS / f"{name}.webp"
    cells = []

    render(header_page(), C("00-header"), ROW_W, 420, 1)
    cells.append(tile("https://dundysm.com", "covers/00-header.webp", shelf["header"]["name"] + ". " + shelf["header"]["intro"], "100%"))

    for i, e in enumerate(shelf["merged"], 1):
        out = C(f"{i:02d}-{slug(e['repo'])}")
        render(merged_cover(e), out, TILE_W, TILE_H, 1.5)
        prs = e["prs"]
        href = (f"https://github.com/{e['repo']}/pull/{prs[0]}" if len(prs) == 1 else
                f"https://github.com/{e['repo']}/pulls?q=is%3Apr+author%3A{USER}+is%3Amerged")
        cells.append(tile(href, f"covers/{out.name}", f"{e['repo']}: {e['title']}", "25%"))

    out = C(f"{len(shelf['merged']) + 1:02d}-in-review")
    render(review_cover(), out, TILE_W, TILE_H, 1.5)
    cells.append(tile(f"https://github.com/search?q=author%3A{USER}+is%3Apr+is%3Aopen+-user%3A{USER}&type=pullrequests",
                      f"covers/{out.name}", "more prs open upstream, in review", "25%"))

    render(label_page("built"), C("50-built"), ROW_W, 150, 1)
    cells.append(tile("https://github.com/dundysm?tab=repositories", "covers/50-built.webp", "built", "100%"))
    for e in shelf["built"]:
        out = C(f"built-{slug(e['name'])}")
        render(built_cover(e), out, TILE_W, TILE_H, 1.5)
        cells.append(tile(f"https://github.com/{e['repo']}", f"covers/{out.name}", f"{e['repo']}: {e['sub']}", "25%"))

    # footer: three equal images so each link is clickable on its own; equal sizes keep their bottom edges level
    third = round(ROW_W / 3)
    for k, (text, url) in enumerate(shelf["links"]):
        out = C(f"99-footer-{k}")
        render(footer_page(esc(text), third), out, third, 140, 1)
        cells.append(tile(url, f"covers/{out.name}", text, "33.333%"))

    readme = "\n".join([
        "<!-- generated by build.py from shelf.json; edit those, not this file -->",
        "<p>" + "".join(cells) + '<br clear="all"></p>',
        "",
    ])
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    print("README.md written")


if __name__ == "__main__":
    check() if "--check" in sys.argv else build()
