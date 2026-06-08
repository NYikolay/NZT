from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector


class Event(Base):
    __tablename__ = "events"

    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_time = Column(DateTime(timezone=True), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    entities_snapshot = Column(JSONB, nullable=False, default=list)
    provenance = Column(JSONB, nullable=False, default=dict)
    embedding = Column(Vector(1536), nullable=True)
    version = Column(Integer, nullable=False, default=1)

    # Связи
    entity_links = relationship(
        "EventEntity", back_populates="event", cascade="all, delete-orphan"
    )
    created_relationships = relationship(
        "Relationship",
        back_populates="created_by_event",
        foreign_keys="Relationship.created_by_event_id",
    )

    __table_args__ = (
        Index("idx_events_user_time", "user_id", "event_time"),
        Index("idx_events_type", "event_type"),
        Index(
            "idx_events_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
