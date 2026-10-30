from typing import Literal

from pydantic import BaseModel

ModelState = Literal["not_trained", "loaded", "error"]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str


class ModelStatusResponse(BaseModel):
    state: ModelState
    loaded: bool
    model_path: str
    classes: int
    message: str


class AnimationInfo(BaseModel):
    gloss: str
    clip_url: str


class AnimationRegistryResponse(BaseModel):
    count: int
    animations: list[AnimationInfo]
    message: str
    invalid: list[str] = []
