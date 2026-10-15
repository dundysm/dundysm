"""Build the profile README: one book cover per upstream repo with merged work, one for open PRs, one per own project.

    uv run --with pillow build.py           render covers/*.webp and README.md from shelf.json
    uv run --with pillow build.py --check   list upstream PRs (merged or open) that shelf.json doesn't cover yet

Titles are written by hand in shelf.json; the open-PR count and its repo count come from `gh` at build time.
Covers are rendered by headless Chrome (fonts: Newsreader and JetBrains Mono from Google Fonts, both OFL).
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


def page(body, bg, accent):
    return f"""<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="{FONTS}"><style>
html,body{{margin:0;background:transparent}}
.c{{position:relative;width:400px;height:600px;box-sizing:border-box;overflow:hidden;border-radius:3px 7px 7px 3px;
   background:radial-gradient(130% 70% at 25% 0%,rgba(255,255,255,.075),transparent 62%),radial-gradient(90% 60% at 80% 110%,rgba(0,0,0,.28),transparent 70%),{bg};
   box-shadow:inset 0 0 0 1px rgba(255,255,255,.07);color:{INK};font-family:'JetBrains Mono',monospace;padding:38px 32px 30px 54px}}
.c:before{{content:"";position:absolute;z-index:3;left:0;top:0;bottom:0;width:22px;
   background:linear-gradient(90deg,rgba(0,0,0,.42),rgba(255,255,255,.08) 55%,rgba(0,0,0,.3))}}
.c:after{{content:"";position:absolute;z-index:3;left:22px;top:0;bottom:0;width:1px;background:rgba(0,0,0,.4);box-shadow:1px 0 0 rgba(255,255,255,.06)}}
.top{{position:relative;z-index:2;display:flex;justify-content:space-between;font-size:15px;letter-spacing:.12em;color:{accent}}}
.top .n{{color:rgba(244,241,235,.42)}}
.rule{{position:relative;z-index:2;width:36px;height:2px;background:{accent};margin-top:14px}}
.pin{{width:100px;height:100px;margin:34px auto 0;padding:7px;border-radius:50%;border:1.5px solid {accent};
   box-shadow:0 14px 34px rgba(0,0,0,.35)}}
.pin .l{{width:100px;height:100px}}
.l{{border-radius:50%;background:#fff;overflow:hidden;display:flex;align-items:center;justify-content:center}}
.l img{{width:78%;height:78%;object-fit:contain}}
.t{{font-family:Newsreader,serif;font-weight:400;font-size:38px;line-height:1.1;letter-spacing:-.005em;margin-top:30px;
   font-variation-settings:'opsz' 48}}
.bot{{position:absolute;z-index:2;left:54px;right:32px;bottom:30px}}
.hr{{height:1px;background:rgba(244,241,235,.14);margin-bottom:16px}}
.org{{font-size:16px;color:rgba(244,241,235,.55)}}
.name{{font-size:22px;font-weight:500;margin-top:3px;word-break:break-all}}
.meta{{display:flex;justify-content:space-between;margin-top:14px;font-size:15px;letter-spacing:.02em}}
.meta .m{{color:{accent}}} .meta .d{{color:rgba(244,241,235,.42)}}
.grid{{display:grid;grid-template-columns:repeat(4,56px);gap:12px;justify-content:center;margin-top:34px}}
.grid .l{{width:56px;height:56px;box-shadow:0 0 0 1.5px rgba(244,241,235,.16),0 8px 18px rgba(0,0,0,.3)}}
.art{{position:absolute;z-index:1;left:23px;right:0;top:0;height:350px}}
.art img{{width:100%;height:100%;object-fit:cover;display:block}}
.art:after{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.5),transparent 26%,transparent 42%,{bg} 98%)}}
.built .top{{color:{INK};text-shadow:0 1px 6px rgba(0,0,0,.6)}} .built .rule{{box-shadow:0 1px 6px rgba(0,0,0,.5)}}
.built .t{{position:absolute;z-index:2;left:54px;right:32px;top:318px;margin:0;font-size:44px}}
.sub{{position:absolute;z-index:2;left:54px;right:32px;top:380px;font-family:Newsreader,serif;font-style:italic;font-size:21px;line-height:1.25;
   color:rgba(244,241,235,.72);font-variation-settings:'opsz' 20}}
</style></head><body>{body}<script>
addEventListener('load', () => {{ for (const im of document.querySelectorAll('.l img')) {{
  const k = document.createElement('canvas'); k.width = k.height = 64; const g = k.getContext('2d');
  g.drawImage(im, 0, 0, 64, 64); const [r, gg, b, a] = g.getImageData(2, 2, 1, 1).data;
  if (a > 200) im.parentElement.style.background = `rgb(${{r}},${{gg}},${{b}})`;
}} }});
</script></body></html>"""


def esc(s):
    return html.escape(s, quote=True)


def bottom(org, name, left, right):
    return (f'<div class="bot"><div class="hr"></div><div class="org">{esc(org)}/</div><div class="name">{esc(name)}</div>'
            f'<div class="meta"><span class="m">{esc(left)}</span><span class="d">{esc(right)}</span></div></div>')


def merged_cover(i, e):
    d = DOM[e["domain"]]; org, name = e["repo"].split("/")
    prs = e["prs"]
    left = f"merged · #{prs[0]}" if len(prs) == 1 else f"{len(prs)} merged · #{prs[0]} +{len(prs) - 1}"
    body = (f'<div class="c"><div class="top"><span>{d["label"]}</span><span class="n">no. {i:02d}</span></div><div class="rule"></div>'
            f'<div class="pin"><div class="l"><img src="{logo(org)}"></div></div><div class="t">{esc(e["title"])}</div>'
            + bottom(org, name, left, e["date"]) + "</div>")
    return page(body, d["bg"], d["accent"])


def review_cover(i, n_open, n_repos, date):
    d = DOM["review"]
    imgs = "".join(f'<div class="l"><img src="{logo(o)}"></div>' for o in shelf["review_orgs"][:16])
    title = shelf["review_title"].format(open=n_open)
    body = (f'<div class="c"><div class="top"><span>{d["label"]}</span><span class="n">no. {i:02d}</span></div><div class="rule"></div>'
            f'<div class="grid">{imgs}</div><div class="t" style="margin-top:34px">{esc(title)}</div>'
            f'<div class="bot"><div class="hr"></div><div class="meta" style="margin-top:0"><span class="m">{n_repos} repos</span>'
            f'<span class="d">{esc(date)}</span></div></div></div>')
    return page(body, d["bg"], d["accent"])


def built_cover(e):
    d = DOM["built"]; org, name = e["repo"].split("/")
    body = (f'<div class="c built"><div class="art"><img src="{data_uri(ROOT / e["art"])}" style="object-position:{e["pos"]}"></div>'
            f'<div class="top"><span>{d["label"]}</span><span class="n"></span></div><div class="rule"></div>'
            f'<div class="t">{esc(e["name"])}</div><div class="sub">{esc(e["sub"])}</div>'
            + bottom(org, name, e["tags"], "") + "</div>")
    return page(body, d["bg"], d["accent"])


def render(html_text, out):
    """HTML -> headless Chrome PNG (2x) -> lossy WebP with alpha; the 20 PNGs were ~6 MB, the WebPs are a fraction."""
    from PIL import Image
    out_png = CACHE / "png" / (out.stem + ".png")
    src = CACHE / "html" / (out.stem + ".html")
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(html_text, encoding="utf-8")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={CACHE / 'chrome'}",
                    "--default-background-color=00000000", "--force-device-scale-factor=2", "--window-size=400,600",
                    "--virtual-time-budget=8000", f"--screenshot={out_png}", src.as_uri()],
                   check=True, capture_output=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.open(out_png).save(out, "WEBP", quality=90, method=6)
    print("  ", out.relative_to(ROOT), f"{out.stat().st_size // 1024} KB")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def cell(href, src, alt):
    return f'<a href="{esc(href)}"><img src="{src}" width="24%" alt="{esc(alt)}"></a>'


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
    open_prs = gh_prs("open")
    n_open = len(open_prs)
    n_open_repos = len({p["repository"]["nameWithOwner"] for p in open_prs})
    merged = shelf["merged"]
    n_merged = sum(len(e["prs"]) for e in merged)
    date = merged[0]["date"]

    for old in [*COVERS.glob("*.png"), *COVERS.glob("*.webp")]:
        old.unlink()
    shelf_cells, built_cells = [], []
    for i, e in enumerate(merged, 1):
        png = COVERS / f"{i:02d}-{slug(e['repo'])}.webp"
        render(merged_cover(i, e), png)
        prs = e["prs"]
        href = (f"https://github.com/{e['repo']}/pull/{prs[0]}" if len(prs) == 1 else
                f"https://github.com/{e['repo']}/pulls?q=is%3Apr+author%3A{USER}+is%3Amerged")
        n = "1 merged pr" if len(prs) == 1 else f"{len(prs)} merged prs"
        shelf_cells.append(cell(href, f"covers/{png.name}", f"{e['repo']}: {e['title']} ({n})"))

    i = len(merged) + 1
    png = COVERS / f"{i:02d}-in-review.webp"
    render(review_cover(i, n_open, n_open_repos, date), png)
    shelf_cells.append(cell(f"https://github.com/search?q=author%3A{USER}+is%3Apr+is%3Aopen+-user%3A{USER}&type=pullrequests",
                            f"covers/{png.name}", f"{n_open} more prs open upstream, in {n_open_repos} repos"))

    for e in shelf["built"]:
        png = COVERS / f"built-{slug(e['name'])}.webp"
        render(built_cover(e), png)
        built_cells.append(cell(f"https://github.com/{e['repo']}", f"covers/{png.name}", f"{e['repo']}: {e['sub']}"))

    intro = shelf["intro"].format(merged=n_merged, repos=len(merged))
    intro = intro.replace(f"{n_merged} merged prs in {len(merged)} repos", f"**{n_merged} merged prs in {len(merged)} repos**")
    links = " · ".join(f"[{t}]({u})" for t, u in shelf["links"])
    readme = "\n".join([
        "<!-- generated by build.py from shelf.json; edit those, not this file -->",
        "",
        intro,
        "",
        "#### merged upstream",
        "",
        "<p>", *shelf_cells, "</p>",
        "",
        "#### built",
        "",
        "<p>", *built_cells, "</p>",
        "",
        f"<sub>{links}</sub>",
        "",
    ])
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    print(f"README.md: {n_merged} merged in {len(merged)} repos, {n_open} open in {n_open_repos} repos")


if __name__ == "__main__":
    check() if "--check" in sys.argv else build()
