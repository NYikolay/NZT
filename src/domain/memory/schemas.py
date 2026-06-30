"""Pydantic schemas for the memory domain."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.memory.models import EntityTypes, EmbeddableType


# ---------------------------------------------------------------------------
# Entity schemas
# ---------------------------------------------------------------------------


class EntityCreate(BaseModel):
    name: str = Field(..., max_length=255)
    entity_type: EntityTypes
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    importance_score: int = Field(default=0, ge=0, le=99)


class EntityUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    entity_type: EntityTypes | None = None
    aliases: list[str] | None = None
    description: str | None = None
    importance_score: int | None = Field(None, ge=0, le=99)


class EntityResponse(BaseModel):
    id: UUID
    name: str
    entity_type: EntityTypes
    aliases: list[str]
    description: str | None
    importance_score: Decimal
    raw_message_id: int
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Event schemas
# ---------------------------------------------------------------------------


class EventCreate(BaseModel):
    summary: str
    timestamp: str | None = None
    importance_score: int = Field(default=0, ge=0, le=99)
    entity_ids: list[UUID] = Field(default_factory=list)


class EventResponse(BaseModel):
    id: UUID
    summary: str
    timestamp: datetime | None
    importance_score: Decimal
    raw_message_id: int
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# RelationshipHistory schemas
# ---------------------------------------------------------------------------


class RelationshipCreate(BaseModel):
    from_entity_id: UUID
    to_entity_id: UUID
    rel_type: str
    valid_from: datetime | None = None
    valid_to: datetime | None = None


class RelationshipResponse(BaseModel):
    id: UUID
    from_entity_id: UUID
    to_entity_id: UUID
    rel_type: str
    valid_from: datetime
    valid_to: datetime | None
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# RawMessage schemas
# ---------------------------------------------------------------------------


class RawMessageCreate(BaseModel):
    content: str


class RawMessageResponse(BaseModel):
    id: int
    content: str
    user_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Embedding schemas
# ---------------------------------------------------------------------------


class EmbeddingCreate(BaseModel):
    embeddable_uuid: UUID | None = None
    embeddable_id: int | None = None
    embeddable_type: EmbeddableType
    embedding: list[float]
    model_version: str
    model_provider: str
    chunk_index: int | None = None
    total_chunks: int | None = None


class EmbeddingResponse(BaseModel):
    id: int
    embeddable_uuid: UUID | None
    embeddable_id: int | None
    embeddable_type: EmbeddableType
    model_version: str
    model_provider: str
    chunk_index: int | None
    total_chunks: int | None
    user_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class EmbeddingSearchResult(BaseModel):
    embeddable_uuid: UUID | None
    embeddable_id: int | None
    embeddable_type: EmbeddableType
    similarity: float
