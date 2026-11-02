import httpx
import pytest

from training import include_stream
from training.include_stream import download

DATA = bytes(range(256)) * 400  # 102,400 bytes


def server(drop_after: int | None = None, honor_range: bool = True):
    """Fake HTTP server. The first request is cut after `drop_after` bytes (as 'peer closed connection') when set."""
    state = {"requests": [], "dropped": False}

    def handler(request: httpx.Request) -> httpx.Response:
        rng = request.headers.get("range")
        state["requests"].append(rng)
        start = int(rng.split("=")[1].split("-")[0]) if rng and honor_range else 0
        body = DATA[start:]
        if drop_after is not None and not state["dropped"]:
            state["dropped"] = True

            def gen():
                yield body[:drop_after]
                raise httpx.ReadError("peer closed connection without sending complete message body")

            return httpx.Response(206 if rng and honor_range else 200, content=gen())
        return httpx.Response(206 if rng and honor_range else 200, content=body)

    return httpx.Client(transport=httpx.MockTransport(handler)), state


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(include_stream.time, "sleep", lambda s: None)


def test_dropped_connection_resumes_from_the_bytes_already_written(tmp_path) -> None:
    client, state = server(drop_after=70_000)
    dest = tmp_path / "a.zip"
    download("http://x/a.zip", dest, len(DATA), client)
    assert dest.read_bytes() == DATA and not (tmp_path / "a.part").exists()
    assert state["requests"] == [None, "bytes=65536-"]  # second request asked only for the rest (whole 64 KiB chunks were kept)


def test_server_that_ignores_range_restarts_from_zero_and_still_ends_correct(tmp_path) -> None:
    client, state = server(drop_after=70_000, honor_range=False)
    dest = tmp_path / "a.zip"
    download("http://x/a.zip", dest, len(DATA), client)
    assert dest.read_bytes() == DATA


def test_existing_part_file_from_an_earlier_run_is_resumed(tmp_path) -> None:
    (tmp_path / "a.part").write_bytes(DATA[:50_000])
    client, state = server()
    download("http://x/a.zip", tmp_path / "a.zip", len(DATA), client)
    assert (tmp_path / "a.zip").read_bytes() == DATA and state["requests"] == ["bytes=50000-"]


def test_complete_file_is_not_downloaded_again_and_wrong_size_is_an_error(tmp_path) -> None:
    (tmp_path / "a.zip").write_bytes(DATA)
    client, state = server()
    download("http://x/a.zip", tmp_path / "a.zip", len(DATA), client)
    assert state["requests"] == []
    with pytest.raises(RuntimeError, match="could not download"):
        download("http://x/b.zip", tmp_path / "b.zip", len(DATA) + 5, client)  # server never has that many bytes
