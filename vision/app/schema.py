"""Strict output contract of the Vision AI service. The model's JSON is validated against it; anything else is refused. There is deliberately NO 'decision', 'verified' or
'authentic' field: the model only describes what it sees (decision D11 / spec section 6)."""
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocType(str, Enum):
    passport = "passport"
    id_card = "id_card"
    driver_license = "driver_license"
    proof_of_address = "proof_of_address"
    other = "other"


class Status(str, Enum):
    ok = "ok"
    partial = "partial"       # something was read, something was not (missing fields, unreadable parts)
    failed = "failed"


class Field_(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str | None = Field(default=None, max_length=300)
    confidence: float | None = Field(default=None, ge=0, le=1)      # the MODEL's own estimate: not a measurement, not proof


class Anomaly(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(max_length=60, pattern=r"^[a-z0-9_]+$")
    description: str = Field(max_length=300)
    severity: str = Field(default="low", pattern=r"^(low|medium|high)$")


class ModelAnswer(BaseModel):
    """What the model must return. Unknown keys are refused."""
    model_config = ConfigDict(extra="forbid")
    document_type: DocType
    extracted_text: str = Field(default="", max_length=6000)
    fields: dict[str, Field_] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list, max_length=30)
    suspicious_visual_anomalies: list[Anomaly] = Field(default_factory=list, max_length=20)
    overall_confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("fields")
    @classmethod
    def _few_fields(cls, v):
        if len(v) > 40:
            raise ValueError("too many fields")
        for k in v:
            if len(k) > 40 or not k.replace("_", "").isalnum():
                raise ValueError("bad field name")
        return v

    @field_validator("missing_information")
    @classmethod
    def _short(cls, v):
        return [s[:120] for s in v]


class ImageQuality(BaseModel):
    """Measured locally with OpenCV (deterministic), NOT by the model."""
    width: int
    height: int
    sharpness: float
    mean_brightness: float
    glare_ratio: float
    usable: bool
    issues: list[str]


class AnalyzeResult(BaseModel):
    request_id: str
    status: Status
    requested_document_type: DocType
    document_type: DocType | None = None
    extracted_text: str = ""
    fields: dict[str, Field_] = Field(default_factory=dict)
    image_quality: ImageQuality
    missing_information: list[str] = Field(default_factory=list)
    suspicious_visual_anomalies: list[Anomaly] = Field(default_factory=list)
    confidence: float | None = None
    model: str
    engine: str
    disclaimer: str = ("Visual reading by a language model: it can misread or invent text. It is NOT proof that the document is authentic or that the person is who they say. "
                       "Check digits, face matching, liveness and a human reviewer remain separate.")
