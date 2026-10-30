from fastapi import APIRouter, Depends, HTTPException

from app.avatar.registry import list_animations
from app.avatar.sign_registry import RegistryError, RegistryReport, build_report
from app.core.config import Settings, get_settings
from app.recognition.landmarks import process_sequence
from app.recognition.model_status import get_model_status
from app.schemas.translation import (
    AvatarPlanRequest,
    AvatarPlanResponse,
    EnglishToGlossRequest,
    EnglishToGlossResponse,
    GlossToEnglishRequest,
    GlossToEnglishResponse,
    VocabularyItem,
    VocabularyResponse,
)
from app.services.avatar_plan import plan_animations
from app.translation.english_to_gloss import english_to_gloss
from app.translation.gloss_to_english import gloss_to_english
from app.translation.vocabulary import Vocabulary, VocabularyError, get_vocabulary
from app.schemas.recognition import RecognitionResponse, SignTranslationResponse
from app.services.recognition_service import recognize, translate_signs
from app.schemas.landmarks import LandmarkSequenceRequest, LandmarkSequenceResponse
from app.schemas.status import AnimationRegistryResponse, HealthResponse, ModelStatusResponse

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name, version=settings.version)


@router.get("/model/status", response_model=ModelStatusResponse)
def model_status(settings: Settings = Depends(get_settings)) -> ModelStatusResponse:
    return get_model_status(settings.model_dir)


@router.get("/avatar/animations", response_model=AnimationRegistryResponse)
def avatar_animations(settings: Settings = Depends(get_settings)) -> AnimationRegistryResponse:
    return list_animations(settings.animation_dir)


@router.post("/landmarks/extract", response_model=LandmarkSequenceResponse)
def landmarks_extract(req: LandmarkSequenceRequest) -> LandmarkSequenceResponse:
    """Validate and normalize a browser-extracted landmark sequence (no video is received)."""
    return process_sequence(req)


@router.post("/signs/recognize", response_model=RecognitionResponse)
def signs_recognize(
    req: LandmarkSequenceRequest, settings: Settings = Depends(get_settings)
) -> RecognitionResponse:
    """503 when no trained model exists; 422 when the landmark sequence is unusable."""
    return recognize(req, settings.model_dir)


def get_vocab(settings: Settings = Depends(get_settings)) -> Vocabulary:
    try:
        return get_vocabulary(settings.translation_config)
    except VocabularyError:
        raise HTTPException(status_code=503, detail="Translation vocabulary is unavailable or invalid.") from None


@router.post("/translation/english-to-gloss", response_model=EnglishToGlossResponse)
def translation_english_to_gloss(
    req: EnglishToGlossRequest, vocab: Vocabulary = Depends(get_vocab)
) -> EnglishToGlossResponse:
    try:
        return english_to_gloss(req.text, vocab)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.post("/translation/gloss-to-english", response_model=GlossToEnglishResponse)
def translation_gloss_to_english(
    req: GlossToEnglishRequest, vocab: Vocabulary = Depends(get_vocab)
) -> GlossToEnglishResponse:
    return gloss_to_english(req.gloss, vocab)


@router.post("/avatar/plan", response_model=AvatarPlanResponse)
def avatar_plan(req: AvatarPlanRequest, settings: Settings = Depends(get_settings)) -> AvatarPlanResponse:
    """Which gloss tokens have a real animation clip, in playback order."""
    return plan_animations(req.gloss, settings.animation_dir)


@router.get("/translation/vocabulary", response_model=VocabularyResponse)
def translation_vocabulary(
    vocab: Vocabulary = Depends(get_vocab), settings: Settings = Depends(get_settings)
) -> VocabularyResponse:
    clips = {a.gloss for a in list_animations(settings.animation_dir).animations}
    items = [VocabularyItem(gloss=g, english=e.english, has_animation=g in clips) for g, e in sorted(vocab.glosses.items())]
    return VocabularyResponse(
        items=items,
        animated=sum(i.has_animation for i in items),
        note="Placeholder vocabulary; a gloss is only signable by the avatar if it has an animation clip.",
    )


@router.post("/signs/translate", response_model=SignTranslationResponse)
def signs_translate(
    req: LandmarkSequenceRequest,
    settings: Settings = Depends(get_settings),
    vocab: Vocabulary = Depends(get_vocab),
) -> SignTranslationResponse:
    """Full sign-to-English pipeline for one isolated sign. 503 without a model, 422 for unusable landmarks."""
    return translate_signs(req, settings.model_dir, vocab, settings.min_confidence)


@router.get("/avatar/registry", response_model=RegistryReport)
def avatar_registry(settings: Settings = Depends(get_settings)) -> RegistryReport:
    """Per-sign provenance and verification status, computed from the registry file and the clips on disk."""
    try:
        return build_report(settings.sign_registry, settings.animation_dir)
    except RegistryError:
        raise HTTPException(status_code=503, detail="Sign registry is unavailable or invalid.") from None
