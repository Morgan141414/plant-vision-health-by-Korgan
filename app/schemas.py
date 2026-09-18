from __future__ import annotations

from pydantic import BaseModel, Field


class PlantResult(BaseModel):
    name: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    mode: str = "unavailable"
    reason: str | None = None


class HealthResult(BaseModel):
    status: str
    confidence: float | None = Field(default=None, ge=0, le=1)


class VegetationResult(BaseModel):
    coverage_percent: float = Field(ge=0, le=100)
    bbox: list[int] | None


class AnalysisResponse(BaseModel):
    mode: str
    plant: PlantResult
    health: HealthResult
    vegetation: VegetationResult
    frame: dict[str, int]
    latency_ms: float = Field(ge=0)
    disclaimer: str
