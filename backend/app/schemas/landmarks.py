from pydantic import BaseModel, Field

MAX_FRAMES = 300


class Point(BaseModel):
    x: float
    y: float
    z: float = 0.0


class LandmarkFrame(BaseModel):
    """One video frame of MediaPipe Holistic landmarks. A missing body part is null."""

    pose: list[Point] | None = Field(default=None, description="33 pose landmarks")
    left_hand: list[Point] | None = Field(default=None, description="21 hand landmarks")
    right_hand: list[Point] | None = Field(default=None, description="21 hand landmarks")


class LandmarkSequenceRequest(BaseModel):
    frames: list[LandmarkFrame] = Field(min_length=1, max_length=MAX_FRAMES)


class FrameReport(BaseModel):
    valid: bool
    has_left_hand: bool
    has_right_hand: bool
    issues: list[str]


class LandmarkSequenceResponse(BaseModel):
    num_frames: int
    feature_dim: int
    valid_frames: int
    frames_with_hands: int
    usable: bool
    warnings: list[str]
    frame_reports: list[FrameReport]
    features: list[list[float]]
