"""ISL-CSLTR: list the remote zip (byte ranges only) and read its CSV file(s). Writes data/datasets/isl_cslrt/listing.json and the CSV(s) next to it.
usage (repository root): python -I tools/extra_datasets/isl_cslrt_inspect.py"""
import collections, json, posixpath, sys, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from range_zip import RangeFile

URL = "https://prod-dcd-datasets-public-files-eu-west-1.s3.eu-west-1.amazonaws.com/5de8c65d-30ba-4362-941f-47d61d435aa0"
SIZE = 8905822924
OUT = Path(__file__).resolve().parents[2] / "data" / "datasets" / "isl_cslrt"
OUT.mkdir(parents=True, exist_ok=True)
rf = RangeFile(URL, SIZE)
z = zipfile.ZipFile(rf)
infos = z.infolist()
ext = collections.Counter(posixpath.splitext(i.filename)[1].lower() for i in infos if not i.is_dir())
size_by_ext = collections.Counter()
for i in infos:
    if not i.is_dir():
        size_by_ext[posixpath.splitext(i.filename)[1].lower()] += i.file_size
tops = collections.Counter("/".join(i.filename.split("/")[:2]) for i in infos if not i.is_dir())
listing = {"entries": len(infos), "by_extension": dict(ext), "uncompressed_bytes_by_extension": dict(size_by_ext), "top_folders": dict(tops.most_common(40)),
           "csv": [i.filename for i in infos if i.filename.lower().endswith(".csv")], "bytes_transferred_for_listing": rf.fetched, "requests": rf.requests}
(OUT / "members.json").write_text(json.dumps([{"name": i.filename, "size": i.file_size, "compressed": i.compress_size, "offset": i.header_offset, "method": i.compress_type} for i in infos]), encoding="utf-8")
small = listing["csv"] + [i.filename for i in infos if i.filename.lower().endswith((".txt", ".xlsx"))]  # the annotation files only (about 0.5 MB)
for name in small:
    data = z.read(name)
    (OUT / posixpath.basename(name)).write_bytes(data)
    listing.setdefault("csv_bytes", {})[name] = len(data)
listing["bytes_transferred_total"] = rf.fetched
(OUT / "listing.json").write_text(json.dumps(listing, indent=1), encoding="utf-8")
print(json.dumps(listing, indent=1)[:3500])
