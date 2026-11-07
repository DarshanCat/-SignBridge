"""How many WLASL video links still answer? A random sample of 300 instances (seed 0), probed without downloading any video:
YouTube links through the public oEmbed endpoint (a tiny JSON answer, 200 for a video that exists), every other host with an HTTP HEAD request (a GET of the first byte
when the host refuses HEAD). A link counts as alive when the answer is a success, and for non YouTube hosts the content type is not a web page (an HTML answer is a
"video removed" page). The result is an estimate for the sample with a Wilson 95 percent interval; it does not prove that a download would succeed.
usage (repository root): python -I tools/extra_datasets/wlasl_probe.py"""
import collections
import json
import math
import random
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
data = json.loads((ROOT / "data" / "datasets" / "wlasl" / "WLASL_v0.3.json").read_text(encoding="utf-8"))
inst = [{"gloss": g["gloss"], **i} for g in data for i in g["instances"]]
sample = random.Random(0).sample(inst, 300)
UA = {"User-Agent": "Mozilla/5.0 (research link check; headers only)"}


def probe(i):
    url = i["url"]
    host = urllib.parse.urlparse(url).netloc.replace("www.", "")
    yt = "youtube.com" in host or "youtu.be" in host
    try:
        if yt:
            req = urllib.request.Request("https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(url, safe=""), headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                return {"video_id": i["video_id"], "host": "youtube", "status": r.status, "alive": r.status == 200, "type": "oembed"}
        req = urllib.request.Request(url, method="HEAD", headers=UA)
        try:
            r = urllib.request.urlopen(req, timeout=20)
        except urllib.error.HTTPError as e:
            if e.code not in (403, 405, 501):
                raise
            r = urllib.request.urlopen(urllib.request.Request(url, headers={**UA, "Range": "bytes=0-0"}), timeout=20)
        ctype = (r.headers.get("Content-Type") or "").lower()
        r.close()
        return {"video_id": i["video_id"], "host": host, "status": r.status, "alive": 200 <= r.status < 300 and "html" not in ctype, "type": ctype}
    except urllib.error.HTTPError as e:
        return {"video_id": i["video_id"], "host": "youtube" if yt else host, "status": e.code, "alive": False, "type": ""}
    except Exception as e:  # noqa: BLE001 - DNS failures, timeouts, resets: the link does not answer
        return {"video_id": i["video_id"], "host": "youtube" if yt else host, "status": None, "alive": False, "type": type(e).__name__}


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


with ThreadPoolExecutor(max_workers=12) as pool:
    res = list(pool.map(probe, sample))
alive = sum(r["alive"] for r in res)
lo, hi = wilson(alive, len(res))
by = collections.defaultdict(lambda: [0, 0])
for r in res:
    by[r["host"]][0] += r["alive"]
    by[r["host"]][1] += 1
out = {"sample": len(res), "alive": alive, "share": alive / len(res), "wilson95": [lo, hi], "by_host": {h: {"alive": a, "n": n} for h, (a, n) in sorted(by.items(), key=lambda kv: -kv[1][1])},
       "statuses": dict(collections.Counter(str(r["status"]) for r in res)), "results": res,
       "note": "headers only; oEmbed for YouTube; an estimate for 300 random instances, not a download test"}
(ROOT / "docs" / "evaluation" / "wlasl_probe.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in out.items() if k != "results"}, indent=1))
