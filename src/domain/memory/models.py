from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum, IntEnum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    ForeignKey,
    Text,
    String,
    Enum,
    Integer,
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


class EntityRelationTypes(str, Enum):
    WORKS_FOR = "WORKS_FOR"
    FRIEND_OF = "FRIEND_OF"
    ASSIGNED_TO = "ASSIGNED_TO"
    MENTIONS = "MENTIONS"
    DISCUSSED_WITH = "DISCUSSED_WITH"
    RELATES_TO = "RELATES_TO"
    CONTRADICTS = "CONTRADICTS"
    PART_OF = "PART_OF"
    OWNS = "OWNS"
    LOCATED_AT = "LOCATED_AT"
    LEADS = "LEADS"
    CREATED_BY = "CREATED_BY"
    SUPERSEDES = "SUPERSEDES"
    UNKNOWN = "UNKNOWN"


class EmbeddableType(str, Enum):
    """Типы сущностей, которые могут иметь эмбеддинги"""

    ENTITIES = "entities"
    EVENTS = "events"


class Event(Base, UUIDMixin, TimestampMixin, UserOwnedMixin):
    __tablename__ = "events"

    __table_args__ = {"comment": "Основная таблица событий."}

    timestamp: Mapped[datetime | None] = mapped_column(
        doc="Упомянутое в контексте время события"
    )
    event_type: Mapped[str] = mapped_column(
        String(65), doc="Тестовое поле, тип события: correction, task_create etc."
    )
    summary: Mapped[str] = mapped_column(
        Text, doc="Небольшое описание события, сгенерированное LLM"
    )
    importance_score: Mapped[Decimal] = mapped_column(
        DECIMAL(3, 0),
        doc="Насколько важно событие в жизни пользователя. 0, 25, 50, 70, 85, 95, 99",
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


class Entity(Base, UUIDMixin, TimestampMixin, UserOwnedMixin):
    __tablename__ = "entities"

    entity_type: Mapped[EntityTypes] = mapped_column(EntityTypes)
    aliases: Mapped[List[str]] = mapped_column(ARRAY(String))
    desctiption: Mapped[Optional[str]] = mapped_column(Text)
    importance_score: Mapped[Decimal] = mapped_column(
        DECIMAL(3, 0), default=Decimal("0")
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
        ForeignKey("entities.id", ondelete="CASCADE"), index=True
    )
    to_entity_id: Mapped[UUID] = mapped_column(
        ForeignKey("entities.id", ondelete="CASCADE"), index=True
    )

    from_entity: Mapped["Entity"] = relationship(
        foreign_keys=[from_entity_id],
        back_populates="outgoing_relations",
    )
    to_entity: Mapped["Entity"] = relationship(
        foreign_keys=[to_entity_id],
        back_populates="incoming_relations",
    )

    rel_type: Mapped[str] = mapped_column(String(125))

    valid_from: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    valid_to: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
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
        # Индекс для поиска действующих записей
        Index("ix_valid_period", "valid_from", "valid_to", postgresql_using="btree"),
    )


class RawMessage(Base, IDMixin, TimestampMixin, UserOwnedMixin):
    __tablename__ = "raw_messages"

    content: Mapped[str] = relationship(Text)

    events: Mapped[List["Event"]] = relationship(back_populates="raw_message")
    entities: Mapped[List["Entity"]] = relationship(back_populates="raw_message")


class Embedding(Base, IDMixin, TimestampMixin):
    __tablename__ = "embeddings"

    embeddable_id: Mapped[UUID] = mapped_column(nullable=False)
    embeddable_type: Mapped[EmbeddableType] = mapped_column(String(20))
    embedding: Mapped[list[float]] = mapped_column(VECTOR(1536))

    model_version: Mapped[str] = mapped_column(
        String(50), doc="Версия модели: text-embedding-3-small, text-embedding-3-large"
    )
    model_provider: Mapped[str] = mapped_column(
        String(50), doc="Провайдер: openai, cohere, huggingface"
    )

    chunk_index: Mapped[int | None] = mapped_column(
        nullable=True, doc="Индекс чанка (0-based). NULL если не чанк"
    )
    total_chunks: Mapped[int | None] = mapped_column(
        nullable=True, doc="Общее количество чанков. NULL если не чанк"
    )

    __table_args__ = (
        Index("ix_embeddings_lookup", "embeddable_type", "embeddable_id"),
        Index(
            "ix_embeddings_vector",
            embedding,
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_embeddings_model", "model_provider", "model_version"),
    )

    def __repr__(self):
        return (
            f"<Embedding("
            f"type={self.embeddable_type}, "
            f"id={self.embeddable_id[:8]}..., "
            f"model={self.model_provider}/{self.model_version}"
            f")>"
        )
