"""Read the directory and single members of a remote zip with HTTP byte range requests, without downloading the archive.

A file like object (seekable, read only) over a URL that answers Range requests; zipfile.ZipFile reads the end of the file (central directory) and any one member
through it. Every byte fetched is counted, so a report can state how much was transferred. usage: see tools/extra_datasets/isl_cslrt_inspect.py"""
import io
import urllib.request


class RangeFile(io.RawIOBase):
    def __init__(self, url: str, size: int, chunk: int = 1 << 18):
        self.url, self.size, self.pos, self.chunk = url, size, 0, chunk
        self.fetched = 0  # bytes transferred
        self.requests = 0
        self._cache: dict[int, bytes] = {}

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        self.pos = {io.SEEK_SET: offset, io.SEEK_CUR: self.pos + offset, io.SEEK_END: self.size + offset}[whence]
        return self.pos

    def _fetch(self, start: int, end: int) -> bytes:
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            if r.status != 206:
                raise OSError(f"the server did not honour the Range request (HTTP {r.status}); refusing to read the whole file")
            data = r.read()
        self.fetched += len(data)
        self.requests += 1
        return data

    def read(self, n=-1):
        if n < 0 or self.pos + n > self.size:
            n = self.size - self.pos
        out, end = bytearray(), self.pos + n
        while self.pos < end:
            block = self.pos // self.chunk
            if block not in self._cache:
                s = block * self.chunk
                self._cache[block] = self._fetch(s, min(s + self.chunk, self.size) - 1)
            data = self._cache[block]
            lo = self.pos - block * self.chunk
            take = data[lo : lo + (end - self.pos)]
            out += take
            self.pos += len(take)
        return bytes(out)

    def readinto(self, b):
        d = self.read(len(b))
        b[: len(d)] = d
        return len(d)
