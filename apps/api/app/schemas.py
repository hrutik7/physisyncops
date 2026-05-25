from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


UploadSource = Literal["shopify_orders", "meta_ads", "inventory", "creative_performance", "customer_signals"]
DecisionState = Literal["pending", "monitoring", "verified", "successful", "unsuccessful", "ignored", "snoozed"]


def to_camel(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class MappingSuggestion(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        ser_json_schema_extra={'by_alias': True}
    )
    
    canonical_field: str
    uploaded_column: str | None
    confidence: float
    alternatives: list[str]
    required: bool


class UploadPreviewResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        ser_json_schema_extra={'by_alias': True}
    )
    
    upload_source: UploadSource
    columns: list[str]
    suggestions: list[MappingSuggestion]
    baseline_mode: bool


class ConfirmMappingRequest(BaseModel):
    brand_id: str
    upload_source: UploadSource
    mapping: dict[str, str]


class SnapshotResponse(BaseModel):
    snapshot_id: str
    snapshot_version: int
    is_baseline: bool
    decisions_created: int
    message: str


class DecisionStateRequest(BaseModel):
    state: DecisionState = Field(description="Only pending human controls are accepted directly: monitoring, ignored, snoozed.")
