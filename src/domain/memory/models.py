from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID

from sqlalchemy import (
    ForeignKey,
    Text,
    String,
    DECIMAL,
    TIMESTAMP,
    func,
    CheckConstraint,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from sqlalchemy.dialects.postgresql import ARRAY
from pgvector.sqlalchemy import VECTOR

from src.core.base_model import Base
from src.core.base_mixins import UUIDMixin, TimestampMixin, IDMixin
from src.domain.users.models_mixins import UserOwnedMixin


class EntityTypes(str, Enum):
    PERSON = "PERSON"
    ORGANIZATION = "ORGANIZATION"
    PROJECT = "PROJECT"
    PRODUCT = "PRODUCT"
    LOCATION = "LOCATION"
    ASSET = "ASSET"
    CONCEPT = "CONCEPT"
    IDENTITY = "IDENTITY"
    GOAL = "GOAL"


# class EntityRelationTypes(str, Enum):
#     WORKS_FOR = "WORKS_FOR"
#     FRIEND_OF = "FRIEND_OF"
#     ASSIGNED_TO = "ASSIGNED_TO"
#     MENTIONS = "MENTIONS"
#     DISCUSSED_WITH = "DISCUSSED_WITH"
#     RELATES_TO = "RELATES_TO"
#     CONTRADICTS = "CONTRADICTS"
#     PART_OF = "PART_OF"
#     OWNS = "OWNS"
#     LOCATED_AT = "LOCATED_AT"
#     LEADS = "LEADS"
#     CREATED_BY = "CREATED_BY"
#     SUPERSEDES = "SUPERSEDES"
#     UNKNOWN = "UNKNOWN"


class EmbeddableType(str, Enum):
    """Types of entities that can have embeddings"""

    ENTITIES = "entities"
    EVENTS = "events"


class Event(Base, UUIDMixin, TimestampMixin, UserOwnedMixin):
    __tablename__ = "events"

    timestamp: Mapped[str | None] = mapped_column(
        doc="The time of the event mentioned in the context"
    )

    summary: Mapped[str] = mapped_column(Text, doc="A brief description of the event")

    importance_score: Mapped[Decimal] = mapped_column(
        DECIMAL(3, 0),
        default=Decimal("0"),
        doc="How important the event is in the user's life. 0, 25, 50, 70, 85, 95, 99",
    )

    raw_message_id: Mapped[int] = mapped_column(
        ForeignKey("raw_messages.id", ondelete="CASCADE"), index=True
    )
    raw_message: Mapped["RawMessage"] = relationship(
        "RawMessage", back_populates="events"
    )

    entities_relations: Mapped[List["EventEntityRelation"]] = relationship(
        back_populates="event"
    )

    def __repr__(self) -> str:
        return f"Event of user - {self.user_id}: {self.summary}"


class EventEntityRelation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "events_entities_relations"

    entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True
    )
    event_id: Mapped[UUID] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), primary_key=True
    )

    entity: Mapped["Entity"] = relationship(back_populates="events_relations")
    event: Mapped["Event"] = relationship(back_populates="entities_relations")

    def __repr__(self) -> str:
        return f"Entity: {self.entity_id} related to Event: {self.event_id}"


class Entity(Base, UUIDMixin, TimestampMixin, UserOwnedMixin):
    __tablename__ = "entities"

    entity_type: Mapped[EntityTypes]
    aliases: Mapped[List[str]] = mapped_column(
        ARRAY(String), doc="List of Variants of the Entity Name "
    )
    description: Mapped[Optional[str]] = mapped_column(Text)

    importance_score: Mapped[Decimal] = mapped_column(
        DECIMAL(3, 0),
        default=Decimal("0"),
        doc="How important the event is in the user's life. 0, 25, 50, 70, 85, 95, 99",
    )

    outgoing_relations: Mapped[List["RelationshipHistory"]] = relationship(
        foreign_keys="[RelationshipHistory.from_entity_id]",
        back_populates="from_entity",
        cascade="all, delete-orphan",
    )
    incoming_relations: Mapped[List["RelationshipHistory"]] = relationship(
        foreign_keys="[RelationshipHistory.to_entity_id]",
        back_populates="to_entity",
        cascade="all, delete-orphan",
    )

    events_relations: Mapped[List["EventEntityRelation"]] = relationship(
        back_populates="entity"
    )

    raw_message_id: Mapped[int] = mapped_column(
        ForeignKey("raw_messages.id", ondelete="CASCADE"), index=True
    )
    raw_message: Mapped["RawMessage"] = relationship(
        "RawMessage", back_populates="entities"
    )


class RelationshipHistory(Base, UUIDMixin, TimestampMixin, UserOwnedMixin):
    __tablename__ = "relationships_history"

    from_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        index=True,
        doc="All entities related to this entity",
    )
    to_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"),
        index=True,
        doc="All entities to which this entity is related",
    )

    from_entity: Mapped["Entity"] = relationship(
        foreign_keys=[from_entity_id],
        back_populates="outgoing_relations",
    )
    to_entity: Mapped["Entity"] = relationship(
        foreign_keys=[to_entity_id],
        back_populates="incoming_relations",
    )

    rel_type: Mapped[str] = mapped_column(
        doc="A logical description of the relationship between entities. For example, WORKS_FOR",
    )

    valid_from: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        doc="At what point does the concept become relevant in the context of the user's life?",
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="Up to what point is the concept relevant in the context of the user's life?",
    )

    def __repr__(self):
        return f"<Relationship(from={self.from_entity_id}, to={self.to_entity_id}, type='{self.rel_type}')>"

    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from", name="ck_valid_period"
        ),
        CheckConstraint("from_entity_id != to_entity_id", name="ck_no_self_relation"),
        UniqueConstraint(
            "from_entity_id",
            "to_entity_id",
            "valid_from",
            name="uq_relationship",
        ),
        Index("ix_valid_period", "valid_from", "valid_to", postgresql_using="btree"),
    )


class RawMessage(Base, IDMixin, TimestampMixin, UserOwnedMixin):
    __tablename__ = "raw_messages"

    content: Mapped[str] = mapped_column(Text)

    events: Mapped[List["Event"]] = relationship(back_populates="raw_message")
    entities: Mapped[List["Entity"]] = relationship(back_populates="raw_message")


class Embedding(Base, IDMixin, TimestampMixin):
    __tablename__ = "embeddings"

    embeddable_uuid: Mapped[UUID | None]
    embeddable_id: Mapped[int | None]
    embeddable_type: Mapped[EmbeddableType] = mapped_column(String(20))
    embedding: Mapped[list[float | int]] = mapped_column(VECTOR(1536))

    model_version: Mapped[str] = mapped_column(
        String(50), doc="Model version: text-embedding-3-small, text-embedding-3-large"
    )
    model_provider: Mapped[str] = mapped_column(
        String(50), doc="Provider: OpenAI, Cohere, Hugging Face"
    )

    chunk_index: Mapped[int | None] = mapped_column(
        nullable=True, doc="Chunk index (0-based). NULL if not a chunk"
    )
    total_chunks: Mapped[int | None] = mapped_column(
        nullable=True, doc="Total number of chunks. NULL if not a chunk"
    )

    __table_args__ = (
        CheckConstraint(
            "(embeddable_uuid IS NOT NULL AND embeddable_id IS NULL) OR "
            "(embeddable_uuid IS NULL AND embeddable_id IS NOT NULL)",
            name="ck_exactly_one_id",
        ),
        Index("ix_embeddings_lookup", "embeddable_type", "embeddable_id"),
        Index(
            "ix_embeddings_vector",
            embedding,
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_embeddings_model", "model_provider", "model_version"),
    )

    @validates("embeddable_uuid", "embeddable_id")
    def validate_exclusive_fields(self, key: str, value: UUID | int):
        if key == "embeddable_uuid" and value is not None:
            if self.embeddable_id is not None:
                raise ValueError(
                    "Нельзя установить embeddable_uuid: embeddable_int_id уже заполнен"
                )
        if key == "embeddable_int_id" and value is not None:
            if self.embeddable_uuid is not None:
                raise ValueError(
                    "Нельзя установить embeddable_int_id: embeddable_uuid уже заполнен"
                )
        return value

    def __repr__(self):
        return (
            f"<Embedding("
            f"type={self.embeddable_type}, "
            f"id={self.embeddable_id[:8]}..., "
            f"model={self.model_provider}/{self.model_version}"
            f")>"
        )


class EntityRelationType(Base, IDMixin, TimestampMixin):
    __tablename__ = "entity_relation_types"

    name: Mapped[str] = mapped_column(String(65), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_preset: Mapped[bool] = mapped_column(default=False, server_default="false")
    is_accepted: Mapped[bool] = mapped_column(default=False, server_default="false")

    def __repr__(self) -> str:
        return (
            f"<EntityRelationType("
            f"id={self.id}, "
            f"name='{self.name}', "
            f"preset={self.is_preset}, "
            f"accepted={self.is_accepted}"
            f")>"
        )


class EntityRelationTypeSuggestion(Base, IDMixin, TimestampMixin):
    __tablename__ = "entity_relation_type_suggestions"

    entity_relation_type_id: Mapped[int] = mapped_column(
        ForeignKey("entity_relation_types.id", ondelete="CASCADE"),
        index=True,
        doc="The suggested relation type",
    )
    raw_message_id: Mapped[int] = mapped_column(
        ForeignKey("raw_messages.id", ondelete="CASCADE"),
        index=True,
        doc="The message that triggered this suggestion",
    )
    reasoning: Mapped[str | None] = mapped_column(
        Text, nullable=True, doc="LLM's reasoning for suggesting this type"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", doc="pending | accepted | rejected"
    )

    relation_type: Mapped["EntityRelationType"] = relationship(
        "EntityRelationType",
        foreign_keys=[entity_relation_type_id],
    )
    raw_message: Mapped["RawMessage"] = relationship(
        "RawMessage", foreign_keys=[raw_message_id]
    )

    def __repr__(self) -> str:
        return (
            f"<EntityRelationTypeSuggestion("
            f"id={self.id}, "
            f"type_id={self.entity_relation_type_id}, "
            f"status='{self.status}'"
            f")>"
        )
