import importlib.util
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("supplement_watchdog", Path(__file__).resolve().parents[2] / "tools" / "supplement_watchdog.py")
wd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wd)


class World:
    """Fake processes: each pid is 'running' for a number of polls, then exits and leaves the log it was given."""

    def __init__(self, tmp_path: Path, outcomes: list[str]) -> None:
        self.tmp = tmp_path
        self.outcomes = outcomes  # one per run: "clean" or an exception line
        self.alive: dict[int, int] = {}
        self.launched: list[int] = []
        self.sleeps: list[float] = []
        self.net_calls = 0
        self.net_down_for = 0
        self.status = tmp_path / "status.md"
        self.status.write_text("# Project status\n\nbody\n", encoding="utf-8")
        self.logs: dict[int, Path] = {}

    def make_run(self, pid: int, idx: int) -> Path:
        log = self.tmp / f"run{idx}.log"
        out = self.outcomes[idx]
        log.write_text("v2 manifest: 10 samples -> x\n" if out == "clean" else "working\n", encoding="utf-8")
        log.with_name(log.name + ".err").write_text("Traceback...\n" + (out if out != "clean" else ""), encoding="utf-8")
        self.alive[pid] = 2
        self.logs[pid] = log
        return log

    def running(self, pid: int) -> bool:
        self.alive[pid] -= 1
        return self.alive[pid] > 0

    def net(self) -> bool:
        self.net_calls += 1
        return self.net_calls > self.net_down_for

    def launch(self, n: int) -> tuple[int, Path]:
        pid = 1000 + n
        self.launched.append(pid)
        return pid, self.make_run(pid, n)


def run(tmp_path, outcomes, net_down_for=0, max_restarts=5):
    w = World(tmp_path, outcomes)
    w.net_down_for = net_down_for
    log0 = w.make_run(1, 0)
    result = wd.watch(1, log0, w.status, w.launch, tmp_path / "wd", running=w.running, net=w.net, sleep=w.sleeps.append, max_restarts=max_restarts, say=lambda *_: None)
    return result, w


def test_clean_exit_does_nothing(tmp_path) -> None:
    result, w = run(tmp_path, ["clean"])
    assert result == "clean" and w.launched == [] and wd.MARKER not in w.status.read_text(encoding="utf-8")
    assert wd.WAIT_BEFORE_RETRY_S not in w.sleeps


def test_error_waits_two_minutes_checks_network_then_relaunches_and_logs(tmp_path) -> None:
    result, w = run(tmp_path, ["RuntimeError: could not download Electronics_1of2.zip", "clean"], net_down_for=2)
    assert result == "clean" and w.launched == [1001]
    assert 120 in w.sleeps and w.net_calls == 3  # waited 2 min, then polled the network until it was back
    text = w.status.read_text(encoding="utf-8")
    assert wd.MARKER in text and "restart 1 of 5" in text and "RuntimeError: could not download Electronics_1of2.zip" in text
    assert "PID 1001" in text and text.startswith("# Project status")


def test_at_most_five_restarts_then_gives_up_and_says_so(tmp_path) -> None:
    err = "OSError: disk full"
    result, w = run(tmp_path, [err] * 7)
    assert result == "gave_up" and len(w.launched) == 5
    text = w.status.read_text(encoding="utf-8")
    assert text.count("restart ") == 5 and "gave up" in text and "after 5 restarts" in text


def test_network_never_returns_stops_without_relaunching(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(wd, "NETWORK_GIVE_UP_S", 90)
    result, w = run(tmp_path, ["RuntimeError: x", "clean"], net_down_for=10_000)
    assert result == "network_timeout" and w.launched == []
    assert "network did not come back" in w.status.read_text(encoding="utf-8")


def test_failure_reason_reads_the_last_exception_line(tmp_path) -> None:
    log = tmp_path / "a.log"
    err = tmp_path / "a.log.err"
    err.write_text("W0000 noise\nTraceback (most recent call last):\n  File x\nRuntimeError: boom\nI0000 later noise\n", encoding="utf-8")
    assert wd.failure_reason(log) == "RuntimeError: boom"
    assert "no error file" in wd.failure_reason(tmp_path / "missing.log")


def test_watchdog_only_reads_pids(tmp_path) -> None:
    src = (Path(wd.__file__)).read_text(encoding="utf-8")
    for forbidden in ("taskkill", "Stop-Process", ".kill(", ".terminate(", "os.kill"):
        assert forbidden not in src
