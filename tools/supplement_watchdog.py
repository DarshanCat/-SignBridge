"""Watchdog for the INCLUDE supplement run. It only watches a process id and starts a NEW run when that run failed; it never signals,
stops or modifies the watched process (or the zip keeper).

    python tools/supplement_watchdog.py --pid 42512 --log data/raw/include/supplement_resume.log --status docs/PROJECT_STATUS.md \
        --cwd backend --log-prefix data/raw/include/supplement_watchdog -- <the exact supplement command>

Behaviour:
  * watched run exits and its log ends with the "v2 manifest:" line  -> clean exit, nothing is done.
  * watched run exits without that line                              -> error: wait 2 minutes, wait until zenodo.org is reachable
                                                                        (checked every 30 s, up to 60 min), then re-launch the same command
                                                                        (it skips zips that already have a record). At most 5 restarts.
  * every restart (and giving up) is appended to docs/PROJECT_STATUS.md under the marker line with the time and the reason.
"""

import argparse
import re
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

MARKER = "<!-- watchdog-log -->"
CLEAN_LINE = "v2 manifest:"
MAX_RESTARTS = 5
WAIT_BEFORE_RETRY_S = 120
NETWORK_POLL_S = 30
NETWORK_GIVE_UP_S = 3600


def is_running(pid: int) -> bool:
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"], capture_output=True, text=True).stdout
    return f'"{pid}"' in out


def network_ok(host: str = "zenodo.org") -> bool:
    try:
        socket.create_connection((socket.gethostbyname(host), 443), timeout=10).close()
        return True
    except OSError:
        return False


def finished_cleanly(log: Path) -> bool:
    try:
        return CLEAN_LINE in log.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False


def failure_reason(log: Path) -> str:
    """Last exception line of the run's stderr file, else a generic note."""
    err = log.with_name(log.name + ".err")
    try:
        lines = [ln.strip() for ln in err.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip()]
    except OSError:
        return "exited without finishing; no error file"
    for ln in reversed(lines):
        if re.match(r"^[\w.]*(Error|Exception|Exit|Interrupt)\b", ln):
            return ln[:300]
    return "exited without finishing (no exception line in the error file)"


def record(status: Path, text: str) -> None:
    """Insert one line right after the marker in the status file, keeping everything else byte for byte."""
    s = status.read_text(encoding="utf-8")
    if MARKER not in s:
        s = s.replace("# Project status\n\n", f"# Project status\n\n## Supplement run watchdog log (automatic)\n\n{MARKER}\n\n", 1)
    s = s.replace(MARKER, f"{MARKER}\n- {text}", 1)
    status.write_text(s, encoding="utf-8")


def stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def watch(
    pid: int, log: Path, status: Path, launch, log_prefix: Path, *, running=is_running, net=network_ok, sleep=time.sleep,
    max_restarts: int = MAX_RESTARTS, say=print,
) -> str:
    """Returns "clean", "gave_up" or "network_timeout". `launch(n)` starts restart number n and returns (pid, log path)."""
    restarts = 0
    while True:
        while running(pid):
            sleep(30)
        if finished_cleanly(log):
            say(f"{stamp()} run {pid} finished cleanly; watchdog does nothing")
            return "clean"
        reason = failure_reason(log)
        if restarts >= max_restarts:
            record(status, f"{stamp()} watchdog gave up: run {pid} failed again after {restarts} restarts ({reason}). Not restarting.")
            return "gave_up"
        say(f"{stamp()} run {pid} failed: {reason}")
        sleep(WAIT_BEFORE_RETRY_S)
        waited = 0
        while not net():
            if waited >= NETWORK_GIVE_UP_S:
                record(status, f"{stamp()} watchdog stopped: run {pid} failed ({reason}) and the network did not come back within {NETWORK_GIVE_UP_S // 60} min.")
                return "network_timeout"
            sleep(NETWORK_POLL_S)
            waited += NETWORK_POLL_S
        restarts += 1
        new_pid, new_log = launch(restarts)
        record(status, f"{stamp()} restart {restarts} of {max_restarts}: run {pid} exited with an error ({reason}); network reachable after "
                       f"{WAIT_BEFORE_RETRY_S + waited} s; relaunched as PID {new_pid} (log {new_log.name}).")
        pid, log = new_pid, new_log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--log", type=Path, required=True, help="stdout log of the watched run (the clean-exit marker is read from it)")
    ap.add_argument("--status", type=Path, required=True)
    ap.add_argument("--cwd", type=Path, required=True)
    ap.add_argument("--log-prefix", type=Path, required=True)
    ap.add_argument("cmd", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not cmd:
        print("Error: give the supplement command after --", file=sys.stderr)
        return 2

    def launch(n: int) -> tuple[int, Path]:
        out = Path(f"{a.log_prefix}_restart{n}.log")
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        with out.open("w") as so, out.with_name(out.name + ".err").open("w") as se:
            p = subprocess.Popen(cmd, cwd=a.cwd, stdout=so, stderr=se, creationflags=flags)
        return p.pid, out

    result = watch(a.pid, a.log, a.status, launch, a.log_prefix)
    print(f"{stamp()} watchdog finished: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
