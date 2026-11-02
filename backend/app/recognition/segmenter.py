"""Sign segmentation on a live landmark stream: finds where one sign starts and ends from hand position and motion.

Works on the normalized 225 value feature rows (shoulder midpoint origin, shoulder width scale; y grows downward). A frame is "engaged" when a
wrist is raised above the rest line AND the wrists have moved recently; hands down, or raised but still for a while, count as rest. A sign
starts after a few engaged frames and ends after a longer run of rest frames. The segment handed to the classifier includes a few rest
frames on both sides, because the training samples start and end with the hands down.

Limit (also in the README): signs signed back to back without the hands ever dropping or pausing are not separated; they come out as one
segment, which is then usually UNRECOGNIZED rather than wrong.
"""

from collections import deque
from dataclasses import dataclass, field

import numpy as np

LEFT_WRIST_Y = 15 * 3 + 1
RIGHT_WRIST_Y = 16 * 3 + 1
LEFT_WRIST_X = 15 * 3
RIGHT_WRIST_X = 16 * 3


@dataclass(frozen=True)
class SegmenterConfig:
    rest_y: float = 2.0  # wrists lower than this (shoulder widths below the shoulder midpoint) are at rest; resting hands sit at about 2.8, hips at 2.7
    start_frames: int = 2  # consecutive engaged frames that open a sign
    end_frames: int = 6  # consecutive rest frames that close it
    still_speed: float = 0.03  # wrist speed (shoulder widths per frame) below which the hands count as still
    still_frames: int = 10  # raised but still for this many frames counts as rest
    pad_before: int = 5  # rest frames kept before the first engaged frame
    pad_after: int = 4  # rest frames kept after the last engaged frame (at most end_frames)
    min_engaged: int = 6  # a segment with fewer engaged frames is noise and is dropped
    max_frames: int = 120  # a sign longer than this is cut here and classified


@dataclass
class Segment:
    start: int  # stream frame index of the first frame handed to the classifier
    end: int  # stream frame index of the last one (inclusive)
    first_engaged: int
    last_engaged: int
    features: np.ndarray = field(repr=False)  # (n, 225)

    @property
    def frames(self) -> int:
        return self.end - self.start + 1


class SignSegmenter:
    """Feed one normalized feature row per frame with `push`; a finished sign comes back as a Segment. `flush` closes an open sign."""

    def __init__(self, cfg: SegmenterConfig | None = None) -> None:
        self.cfg = cfg or SegmenterConfig()
        self.reset()

    def reset(self) -> None:
        self.index = -1
        self._rows: deque[tuple[int, np.ndarray]] = deque(maxlen=self.cfg.max_frames + self.cfg.pad_before + self.cfg.end_frames + 8)
        self._prev: np.ndarray | None = None
        self._speeds: deque[float] = deque(maxlen=self.cfg.still_frames)
        self._engaged_run = 0
        self._rest_run = 0
        self._open: tuple[int, int] | None = None  # (first engaged index, last engaged index) of the sign in progress
        self._engaged_count = 0

    @property
    def active(self) -> bool:
        """True while a sign is being signed (the first frames of a sign, before it opens, are not reported)."""
        return self._open is not None

    def _engaged(self, row: np.ndarray) -> bool:
        wrists = np.array([row[LEFT_WRIST_X], row[LEFT_WRIST_Y], row[RIGHT_WRIST_X], row[RIGHT_WRIST_Y]])
        speed = 0.0 if self._prev is None else float(max(np.linalg.norm(wrists[:2] - self._prev[:2]), np.linalg.norm(wrists[2:] - self._prev[2:])))
        self._prev = wrists
        self._speeds.append(speed)
        raised = min(row[LEFT_WRIST_Y], row[RIGHT_WRIST_Y]) < self.cfg.rest_y
        moving = max(self._speeds) > self.cfg.still_speed if len(self._speeds) >= self.cfg.still_frames else True
        return bool(raised and moving)

    def push(self, row: np.ndarray) -> list[Segment]:
        """One frame with a usable body pose. Returns the signs that finished with this frame (zero or one)."""
        self.index += 1
        i, cfg = self.index, self.cfg
        self._rows.append((i, row))
        if self._engaged(row):
            self._engaged_run += 1
            self._rest_run = 0
            if self._open is None and self._engaged_run >= cfg.start_frames:
                first = i - self._engaged_run + 1
                self._open = (first, i)
                self._engaged_count = self._engaged_run
            elif self._open is not None:
                self._open = (self._open[0], i)
                self._engaged_count += 1
        else:
            self._engaged_run = 0
            self._rest_run += 1
            if self._open is not None and self._rest_run >= cfg.end_frames:
                return self._close()
        if self._open is not None and i - self._open[0] + 1 >= cfg.max_frames:
            return self._close()
        return []

    def flush(self) -> list[Segment]:
        return self._close() if self._open is not None else []

    def _close(self) -> list[Segment]:
        assert self._open is not None
        first, last = self._open
        engaged = self._engaged_count
        self._open = None
        self._engaged_count = 0
        self._engaged_run = 0
        if engaged < self.cfg.min_engaged:
            return []
        start = max(first - self.cfg.pad_before, self._rows[0][0])
        end = min(last + self.cfg.pad_after, self.index)
        feats = np.stack([r for k, r in self._rows if start <= k <= end])
        return [Segment(start=start, end=end, first_engaged=first, last_engaged=last, features=feats)]
