from typing import Literal

from pydantic import BaseModel, Field

TokenStatus = Literal["mapped", "dropped", "unsupported"]


class EnglishToGlossRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)


class WordResult(BaseModel):
    word: str
    gloss: list[str]
    status: TokenStatus


class EnglishToGlossResponse(BaseModel):
    gloss: list[str]
    words: list[WordResult]
    unsupported: list[str]
    coverage: float = Field(description="supported content words / content words (stopwords excluded)")
    note: str


class GlossToEnglishRequest(BaseModel):
    gloss: list[str] = Field(min_length=1, max_length=50)


class GlossToEnglishResponse(BaseModel):
    english: str
    gloss: list[str]
    unsupported: list[str]
    note: str


class AvatarPlanRequest(BaseModel):
    gloss: list[str] = Field(min_length=1, max_length=50)


class PlanStep(BaseModel):
    gloss: str
    available: bool
    clip_url: str | None


class AvatarPlanResponse(BaseModel):
    steps: list[PlanStep]
    missing: list[str]
    playable: bool
    message: str


class VocabularyItem(BaseModel):
    gloss: str
    english: str
    has_animation: bool


class VocabularyResponse(BaseModel):
    items: list[VocabularyItem]
    animated: int
    note: str
