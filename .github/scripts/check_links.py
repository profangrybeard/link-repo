#!/usr/bin/env python3
"""Check every URL in links.json. Prints a Markdown report to stdout and exits 1 if
anything is broken. 403/429 are reported separately as "blocked": those sites refuse
automated requests and are almost always fine in a real browser. Stdlib only."""

import json, ssl, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36 link-repo-check"
TIMEOUT = 20
BLOCKED = {401, 403, 429, 503}

ctx = ssl.create_default_context()

def fetch(url, method):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
        return r.status, r.geturl()

def check(item):
    url = item["u"]
    for method in ("HEAD", "GET"):
        try:
            status, final = fetch(url, method)
            moved = urlparse(final).netloc.replace("www.", "") != urlparse(url).netloc.replace("www.", "")
            return item, status, final if moved else None, None
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (405, 404, 403, 400):
                continue  # plenty of servers refuse HEAD; try GET before judging
            return item, e.code, None, None
        except Exception as e:
            if method == "HEAD":
                continue
            return item, None, None, type(e).__name__
    return item, None, None, "unreachable"

def main():
    data = json.load(open("links.json"))
    items = [dict(it, cat=c["name"]) for c in data["categories"] for it in c["items"]]
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(check, items))

    broken, blocked, moved = [], [], []
    for item, status, final, err in results:
        line = f"- **{item['cat']}** · {item['t']}  \n  {item['u']}"
        if err or (status and status >= 400 and status not in BLOCKED):
            broken.append(f"{line}  \n  `{err or status}`")
        elif status in BLOCKED:
            blocked.append(f"{line}  \n  `{status}` (refuses bots; open it by hand)")
        elif final:
            moved.append(f"{line}  \n  now redirects off-domain to {final}")

    out = [f"Checked {len(items)} links.\n"]
    if broken:
        out += ["## Broken (fix these)\n", *broken, ""]
    if moved:
        out += ["## Redirected off-domain (check the new home)\n", *moved, ""]
    if blocked:
        out += ["## Blocked automated check (probably fine)\n", *blocked, ""]
    if not (broken or moved or blocked):
        out.append("All links respond.")
    print("\n".join(out))
    sys.exit(1 if broken or moved else 0)

if __name__ == "__main__":
    main()
