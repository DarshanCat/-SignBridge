from pydantic import BaseModel


class SignPrediction(BaseModel):
    label: str
    confidence: float


class RecognitionResponse(BaseModel):
    predictions: list[SignPrediction]
    num_frames_used: int


class SignTranslationResponse(BaseModel):
    """Result of the full sign-to-English pipeline for ONE isolated sign window."""

    predictions: list[SignPrediction]
    num_frames_used: int
    accepted: bool
    min_confidence: float
    gloss: list[str]
    english: str
    unsupported: list[str]
    message: str
