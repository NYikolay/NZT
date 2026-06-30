"""Tests for memory domain repositories — CRUD and query operations."""

from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.memory.models import (
    Entity,
    EntityTypes,
    Event,
    EventEntityRelation,
    RelationshipHistory,
    RawMessage,
    Embedding,
    EmbeddableType,
    EntityRelationType,
    EntityRelationTypeSuggestion,
)
from src.domain.memory.repositories import (
    EntityRepository,
    EventRepository,
    RelationshipHistoryRepository,
    RawMessageRepository,
    EmbeddingRepository,
    EntityRelationTypeRepository,
)


# ---------------------------------------------------------------------------
# EntityRepository tests
# ---------------------------------------------------------------------------


class TestEntityRepository:
    """Tests for EntityRepository."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, session):
        return EntityRepository(session=session)

    @staticmethod
    def _mock_execute(session, return_value):
        """Helper to set up session.execute to return a mock with scalars().all() chain."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = return_value
        session.execute = AsyncMock(return_value=mock_result)

    @pytest.mark.asyncio
    async def test_should_create_entity(self, repo, session):
        user_id = uuid4()
        entity = await repo.create(
            name="Alice",
            entity_type=EntityTypes.PERSON,
            aliases=["Ali"],
            description="A person",
            importance_score=50,
            raw_message_id=1,
            user_id=user_id,
        )
        assert isinstance(entity, Entity)
        assert entity.name == "Alice"
        assert entity.entity_type == EntityTypes.PERSON
        assert entity.aliases == ["Ali"]
        assert entity.description == "A person"
        assert entity.importance_score == 50
        assert entity.raw_message_id == 1
        assert entity.user_id == user_id
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_create_entity_without_optional_fields(self, repo, session):
        user_id = uuid4()
        entity = await repo.create(
            name="Bob",
            entity_type=EntityTypes.PERSON,
            raw_message_id=2,
            user_id=user_id,
        )
        assert entity.name == "Bob"
        assert entity.aliases == []
        assert entity.description is None
        assert entity.importance_score == 0

    @pytest.mark.asyncio
    async def test_should_get_entity_by_id(self, repo, session):
        entity_id = uuid4()
        expected = Entity(
            id=entity_id,
            name="Alice",
            entity_type=EntityTypes.PERSON,
            raw_message_id=1,
            user_id=uuid4(),
        )
        session.get = AsyncMock(return_value=expected)

        result = await repo.get_by_id(entity_id)
        assert result is not None
        assert result.id == entity_id
        assert result.name == "Alice"
        session.get.assert_awaited_once_with(Entity, entity_id)

    @pytest.mark.asyncio
    async def test_should_return_none_when_entity_not_found(self, repo, session):
        session.get = AsyncMock(return_value=None)
        result = await repo.get_by_id(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_should_get_entity_by_name_and_user(self, repo, session):
        user_id = uuid4()
        expected = Entity(
            name="Alice",
            entity_type=EntityTypes.PERSON,
            raw_message_id=1,
            user_id=user_id,
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=expected)
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_name_and_user("Alice", user_id)
        assert result is not None
        assert result.name == "Alice"
        assert result.user_id == user_id

    @pytest.mark.asyncio
    async def test_should_return_none_when_name_not_found(self, repo, session):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.get_by_name_and_user("Nonexistent", uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_should_find_entities_by_alias(self, repo, session):
        user_id = uuid4()
        entity = Entity(
            name="AcmeCorp",
            entity_type=EntityTypes.ORGANIZATION,
            aliases=["ACME", "Acme Inc."],
            raw_message_id=1,
            user_id=user_id,
        )
        self._mock_execute(session, [entity])

        results = await repo.find_by_alias("ACME", user_id)
        assert len(results) == 1
        assert results[0].name == "AcmeCorp"

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_alias_not_found(self, repo, session):
        self._mock_execute(session, [])

        results = await repo.find_by_alias("Unknown", uuid4())
        assert results == []

    @pytest.mark.asyncio
    async def test_should_list_entities_by_user(self, repo, session):
        user_id = uuid4()
        entities = [
            Entity(
                name="Alice",
                entity_type=EntityTypes.PERSON,
                raw_message_id=1,
                user_id=user_id,
            ),
            Entity(
                name="Bob",
                entity_type=EntityTypes.PERSON,
                raw_message_id=2,
                user_id=user_id,
            ),
        ]
        self._mock_execute(session, entities)

        results = await repo.list_by_user(user_id)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_should_list_entities_filtered_by_type(self, repo, session):
        user_id = uuid4()
        entity = Entity(
            name="AcmeCorp",
            entity_type=EntityTypes.ORGANIZATION,
            raw_message_id=1,
            user_id=user_id,
        )
        self._mock_execute(session, [entity])

        results = await repo.list_by_user(user_id, entity_type=EntityTypes.ORGANIZATION)
        assert len(results) == 1
        assert results[0].entity_type == EntityTypes.ORGANIZATION

    @pytest.mark.asyncio
    async def test_should_list_entities_with_pagination(self, repo, session):
        self._mock_execute(session, [])

        results = await repo.list_by_user(uuid4(), limit=10, offset=20)
        assert results == []

    @pytest.mark.asyncio
    async def test_should_update_entity_fields(self, repo, session):
        entity = Entity(
            name="OldName",
            entity_type=EntityTypes.PERSON,
            raw_message_id=1,
            user_id=uuid4(),
        )
        result = await repo.update(entity, name="NewName", description="Updated")
        assert result.name == "NewName"
        assert result.description == "Updated"
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_ignore_unknown_fields_on_update(self, repo, session):
        entity = Entity(
            name="Alice",
            entity_type=EntityTypes.PERSON,
            raw_message_id=1,
            user_id=uuid4(),
        )
        result = await repo.update(entity, name="Bob", nonexistent_field="value")
        assert result.name == "Bob"
        session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# EventRepository tests
# ---------------------------------------------------------------------------


class TestEventRepository:
    """Tests for EventRepository."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, session):
        return EventRepository(session=session)

    @staticmethod
    def _mock_execute(session, return_value):
        """Helper to set up session.execute to return a mock with scalars().all() chain."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = return_value
        session.execute = AsyncMock(return_value=mock_result)

    @pytest.mark.asyncio
    async def test_should_create_event(self, repo, session):
        user_id = uuid4()
        event = await repo.create(
            summary="Meeting with Alice",
            importance_score=50,
            raw_message_id=1,
            user_id=user_id,
        )
        assert isinstance(event, Event)
        assert event.summary == "Meeting with Alice"
        assert event.importance_score == 50
        assert event.raw_message_id == 1
        assert event.user_id == user_id
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_create_event_with_timestamp(self, repo, session):
        event = await repo.create(
            summary="Event with timestamp",
            timestamp="2024-01-01T00:00:00Z",
            raw_message_id=2,
            user_id=uuid4(),
        )
        assert event.summary == "Event with timestamp"
        assert event.timestamp == "2024-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_should_get_event_by_id(self, repo, session):
        event_id = uuid4()
        expected = Event(
            id=event_id,
            summary="Test event",
            raw_message_id=1,
            user_id=uuid4(),
        )
        session.get = AsyncMock(return_value=expected)

        result = await repo.get_by_id(event_id)
        assert result is not None
        assert result.id == event_id
        assert result.summary == "Test event"
        session.get.assert_awaited_once_with(Event, event_id)

    @pytest.mark.asyncio
    async def test_should_return_none_when_event_not_found(self, repo, session):
        session.get = AsyncMock(return_value=None)
        result = await repo.get_by_id(uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_should_list_events_by_user(self, repo, session):
        user_id = uuid4()
        events = [
            Event(summary="Event 1", raw_message_id=1, user_id=user_id),
            Event(summary="Event 2", raw_message_id=2, user_id=user_id),
        ]
        self._mock_execute(session, events)

        results = await repo.list_by_user(user_id)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_should_list_events_with_pagination(self, repo, session):
        self._mock_execute(session, [])

        results = await repo.list_by_user(uuid4(), limit=5, offset=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_should_list_events_by_entity(self, repo, session):
        entity_id = uuid4()
        events = [
            Event(summary="Event for entity", raw_message_id=1, user_id=uuid4()),
        ]
        self._mock_execute(session, events)

        results = await repo.list_by_entity(entity_id)
        assert len(results) == 1
        assert results[0].summary == "Event for entity"

    @pytest.mark.asyncio
    async def test_should_link_entity_to_event(self, repo, session):
        event_id = uuid4()
        entity_id = uuid4()
        relation = await repo.link_entity(event_id=event_id, entity_id=entity_id)
        assert isinstance(relation, EventEntityRelation)
        assert relation.event_id == event_id
        assert relation.entity_id == entity_id
        session.add.assert_called_once()
        session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# RelationshipHistoryRepository tests
# ---------------------------------------------------------------------------


class TestRelationshipHistoryRepository:
    """Tests for RelationshipHistoryRepository."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, session):
        return RelationshipHistoryRepository(session=session)

    @staticmethod
    def _mock_execute(session, return_value):
        """Helper to set up session.execute to return a mock with scalars().all() chain."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = return_value
        session.execute = AsyncMock(return_value=mock_result)

    @pytest.mark.asyncio
    async def test_should_create_relationship(self, repo, session):
        from_id = uuid4()
        to_id = uuid4()
        user_id = uuid4()
        rel = await repo.create(
            from_entity_id=from_id,
            to_entity_id=to_id,
            rel_type="WORKS_FOR",
            user_id=user_id,
        )
        assert isinstance(rel, RelationshipHistory)
        assert rel.from_entity_id == from_id
        assert rel.to_entity_id == to_id
        assert rel.rel_type == "WORKS_FOR"
        assert rel.user_id == user_id
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_create_relationship_with_valid_dates(self, repo, session):
        from datetime import datetime, timezone

        valid_from = datetime.now(timezone.utc)
        rel = await repo.create(
            from_entity_id=uuid4(),
            to_entity_id=uuid4(),
            rel_type="RELATES_TO",
            user_id=uuid4(),
            valid_from=valid_from,
        )
        assert rel.valid_from == valid_from

    @pytest.mark.asyncio
    async def test_should_find_relationships_by_entity(self, repo, session):
        entity_id = uuid4()
        rels = [
            RelationshipHistory(
                from_entity_id=entity_id,
                to_entity_id=uuid4(),
                rel_type="WORKS_FOR",
                user_id=uuid4(),
            ),
            RelationshipHistory(
                from_entity_id=uuid4(),
                to_entity_id=entity_id,
                rel_type="MANAGES",
                user_id=uuid4(),
            ),
        ]
        self._mock_execute(session, rels)

        results = await repo.find_by_entity(entity_id)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_no_relationships(self, repo, session):
        self._mock_execute(session, [])

        results = await repo.find_by_entity(uuid4())
        assert results == []

    @pytest.mark.asyncio
    async def test_should_find_relationships_between_entities(self, repo, session):
        entity_a = uuid4()
        entity_b = uuid4()
        rel = RelationshipHistory(
            from_entity_id=entity_a,
            to_entity_id=entity_b,
            rel_type="WORKS_FOR",
            user_id=uuid4(),
        )
        self._mock_execute(session, [rel])

        results = await repo.find_between(entity_a, entity_b)
        assert len(results) == 1
        assert results[0].from_entity_id == entity_a
        assert results[0].to_entity_id == entity_b

    @pytest.mark.asyncio
    async def test_should_find_relationships_between_entities_reverse(
        self, repo, session
    ):
        entity_a = uuid4()
        entity_b = uuid4()
        rel = RelationshipHistory(
            from_entity_id=entity_b,
            to_entity_id=entity_a,
            rel_type="MANAGES",
            user_id=uuid4(),
        )
        self._mock_execute(session, [rel])

        results = await repo.find_between(entity_a, entity_b)
        assert len(results) == 1
        assert results[0].from_entity_id == entity_b
        assert results[0].to_entity_id == entity_a

    @pytest.mark.asyncio
    async def test_should_return_empty_when_no_relationship_between(
        self, repo, session
    ):
        self._mock_execute(session, [])

        results = await repo.find_between(uuid4(), uuid4())
        assert results == []


# ---------------------------------------------------------------------------
# RawMessageRepository tests
# ---------------------------------------------------------------------------


class TestRawMessageRepository:
    """Tests for RawMessageRepository."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, session):
        return RawMessageRepository(session=session)

    @staticmethod
    def _mock_execute(session, return_value):
        """Helper to set up session.execute to return a mock with scalars().all() chain."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = return_value
        session.execute = AsyncMock(return_value=mock_result)

    @pytest.mark.asyncio
    async def test_should_create_raw_message(self, repo, session):
        user_id = uuid4()
        msg = await repo.create(content="Hello world", user_id=user_id)
        assert isinstance(msg, RawMessage)
        assert msg.content == "Hello world"
        assert msg.user_id == user_id
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_get_raw_message_by_id(self, repo, session):
        expected = RawMessage(id=42, content="Test", user_id=uuid4())
        session.get = AsyncMock(return_value=expected)

        result = await repo.get_by_id(42)
        assert result is not None
        assert result.id == 42
        assert result.content == "Test"
        session.get.assert_awaited_once_with(RawMessage, 42)

    @pytest.mark.asyncio
    async def test_should_return_none_when_message_not_found(self, repo, session):
        session.get = AsyncMock(return_value=None)
        result = await repo.get_by_id(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_should_list_messages_by_user(self, repo, session):
        user_id = uuid4()
        messages = [
            RawMessage(id=1, content="First", user_id=user_id),
            RawMessage(id=2, content="Second", user_id=user_id),
        ]
        self._mock_execute(session, messages)

        results = await repo.list_by_user(user_id)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_should_list_messages_with_pagination(self, repo, session):
        self._mock_execute(session, [])

        results = await repo.list_by_user(uuid4(), limit=10, offset=5)
        assert results == []


# ---------------------------------------------------------------------------
# EmbeddingRepository tests
# ---------------------------------------------------------------------------


class TestEmbeddingRepository:
    """Tests for EmbeddingRepository."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, session):
        return EmbeddingRepository(session=session)

    @staticmethod
    def _mock_execute(session, return_value):
        """Helper to set up session.execute to return a mock with scalars().all() chain."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = return_value
        session.execute = AsyncMock(return_value=mock_result)

    @pytest.mark.asyncio
    async def test_should_create_embedding_with_uuid(self, repo, session):
        user_id = uuid4()
        emb = await repo.create(
            embeddable_uuid=uuid4(),
            embeddable_type=EmbeddableType.ENTITIES,
            embedding=[0.1, 0.2, 0.3],
            model_version="text-embedding-3-small",
            model_provider="OpenAI",
            user_id=user_id,
        )
        assert isinstance(emb, Embedding)
        assert emb.embeddable_type == EmbeddableType.ENTITIES
        assert emb.model_version == "text-embedding-3-small"
        assert emb.model_provider == "OpenAI"
        assert emb.user_id == user_id
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_create_embedding_with_id(self, repo, session):
        emb = await repo.create(
            embeddable_id=42,
            embeddable_type=EmbeddableType.EVENTS,
            embedding=[0.4, 0.5],
            model_version="v1",
            model_provider="Cohere",
            user_id=uuid4(),
        )
        assert emb.embeddable_id == 42
        assert emb.embeddable_type == EmbeddableType.EVENTS

    @pytest.mark.asyncio
    async def test_should_create_embedding_with_chunks(self, repo, session):
        emb = await repo.create(
            embeddable_uuid=uuid4(),
            embeddable_type=EmbeddableType.ENTITIES,
            embedding=[0.1, 0.2],
            model_version="v1",
            model_provider="OpenAI",
            user_id=uuid4(),
            chunk_index=0,
            total_chunks=3,
        )
        assert emb.chunk_index == 0
        assert emb.total_chunks == 3

    @pytest.mark.asyncio
    async def test_should_search_similar_embeddings(self, repo, session):
        user_id = uuid4()
        emb = Embedding(
            embeddable_uuid=uuid4(),
            embeddable_type=EmbeddableType.ENTITIES,
            embedding=[0.1, 0.2],
            model_version="v1",
            model_provider="OpenAI",
            user_id=user_id,
        )
        # Mock the cosine_distance and the execute result
        mock_distance = MagicMock()
        mock_distance.__sub__ = MagicMock(return_value=MagicMock())
        mock_distance.__lt__ = MagicMock(return_value=MagicMock())

        session.execute = AsyncMock()
        session.execute.return_value.all = MagicMock(return_value=[(emb, 0.95)])

        results = await repo.search_similar(
            query_vector=[0.1, 0.2],
            user_id=user_id,
            limit=10,
            threshold=0.7,
        )
        assert len(results) == 1
        assert results[0][0] == emb
        assert results[0][1] == 0.95

    @pytest.mark.asyncio
    async def test_should_search_similar_filtered_by_type(self, repo, session):
        user_id = uuid4()
        session.execute = AsyncMock()
        session.execute.return_value.all = MagicMock(return_value=[])

        results = await repo.search_similar(
            query_vector=[0.1, 0.2],
            embeddable_type=EmbeddableType.EVENTS,
            user_id=user_id,
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_should_delete_embeddings_by_uuid(self, repo, session):
        embeddable_uuid = uuid4()
        emb = Embedding(
            embeddable_uuid=embeddable_uuid,
            embeddable_type=EmbeddableType.ENTITIES,
            embedding=[0.1],
            model_version="v1",
            model_provider="OpenAI",
            user_id=uuid4(),
        )
        self._mock_execute(session, [emb])

        await repo.delete_by_embeddable(embeddable_uuid=embeddable_uuid)
        session.delete.assert_called_once_with(emb)
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_delete_embeddings_by_id(self, repo, session):
        emb = Embedding(
            embeddable_id=42,
            embeddable_type=EmbeddableType.EVENTS,
            embedding=[0.1],
            model_version="v1",
            model_provider="OpenAI",
            user_id=uuid4(),
        )
        self._mock_execute(session, [emb])

        await repo.delete_by_embeddable(embeddable_id=42)
        session.delete.assert_called_once_with(emb)
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_do_nothing_when_no_embeddings_to_delete(self, repo, session):
        self._mock_execute(session, [])

        await repo.delete_by_embeddable(embeddable_uuid=uuid4())
        session.delete.assert_not_called()
        session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# EntityRelationTypeRepository tests
# ---------------------------------------------------------------------------


class TestEntityRelationTypeRepository:
    """Tests for EntityRelationTypeRepository."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def repo(self, session):
        return EntityRelationTypeRepository(session=session)

    @staticmethod
    def _mock_execute(session, return_value):
        """Helper to set up session.execute to return a mock with scalars().all() chain."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = return_value
        session.execute = AsyncMock(return_value=mock_result)

    @pytest.mark.asyncio
    async def test_should_create_type(self, repo, session):
        rel_type = await repo.create_type(
            name="WORKS_FOR",
            description="Employment relationship",
            is_preset=True,
            is_accepted=True,
        )
        assert isinstance(rel_type, EntityRelationType)
        assert rel_type.name == "WORKS_FOR"
        assert rel_type.description == "Employment relationship"
        assert rel_type.is_preset is True
        assert rel_type.is_accepted is True
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_create_type_with_defaults(self, repo, session):
        rel_type = await repo.create_type(name="CUSTOM_TYPE")
        assert rel_type.name == "CUSTOM_TYPE"
        assert rel_type.is_preset is False
        assert rel_type.is_accepted is False

    @pytest.mark.asyncio
    async def test_should_get_type_by_name(self, repo, session):
        expected = EntityRelationType(id=1, name="WORKS_FOR", is_accepted=True)
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=expected
        )

        result = await repo.get_by_name("WORKS_FOR")
        assert result is not None
        assert result.id == 1
        assert result.name == "WORKS_FOR"

    @pytest.mark.asyncio
    async def test_should_return_none_when_type_not_found_by_name(self, repo, session):
        session.execute = AsyncMock()
        session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        result = await repo.get_by_name("NONEXISTENT")
        assert result is None

    @pytest.mark.asyncio
    async def test_should_get_type_by_id(self, repo, session):
        expected = EntityRelationType(id=5, name="MANAGES")
        session.get = AsyncMock(return_value=expected)

        result = await repo.get_by_id(5)
        assert result is not None
        assert result.id == 5
        assert result.name == "MANAGES"
        session.get.assert_awaited_once_with(EntityRelationType, 5)

    @pytest.mark.asyncio
    async def test_should_return_none_when_type_not_found_by_id(self, repo, session):
        session.get = AsyncMock(return_value=None)
        result = await repo.get_by_id(999)
        assert result is None

    @pytest.mark.asyncio
    async def test_should_list_all_types(self, repo, session):
        types = [
            EntityRelationType(id=1, name="MANAGES"),
            EntityRelationType(id=2, name="WORKS_FOR"),
        ]
        self._mock_execute(session, types)

        results = await repo.list_all()
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_should_create_suggestion(self, repo, session):
        user_id = uuid4()
        suggestion = await repo.create_suggestion(
            entity_relation_type_id=1,
            raw_message_id=42,
            user_id=user_id,
            reasoning="LLM suggestion",
        )
        assert isinstance(suggestion, EntityRelationTypeSuggestion)
        assert suggestion.entity_relation_type_id == 1
        assert suggestion.raw_message_id == 42
        assert suggestion.user_id == user_id
        assert suggestion.reasoning == "LLM suggestion"
        assert suggestion.status == "pending"
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_create_suggestion_without_reasoning(self, repo, session):
        suggestion = await repo.create_suggestion(
            entity_relation_type_id=2,
            raw_message_id=100,
            user_id=uuid4(),
        )
        assert suggestion.reasoning is None
        assert suggestion.status == "pending"

    @pytest.mark.asyncio
    async def test_should_get_pending_suggestions(self, repo, session):
        suggestions = [
            EntityRelationTypeSuggestion(
                id=1,
                entity_relation_type_id=5,
                raw_message_id=42,
                user_id=uuid4(),
                status="pending",
            ),
        ]
        self._mock_execute(session, suggestions)

        results = await repo.get_pending_suggestions()
        assert len(results) == 1
        assert results[0].status == "pending"

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_no_pending_suggestions(
        self, repo, session
    ):
        self._mock_execute(session, [])

        results = await repo.get_pending_suggestions()
        assert results == []
