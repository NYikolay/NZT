"""Tests for memory domain repositories."""

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
    RawMessageRoles,
    Embedding,
    EmbeddableType,
)
from src.domain.memory.repositories import (
    EntityRepository,
    EventRepository,
    RelationshipHistoryRepository,
    RawMessageRepository,
    EmbeddingRepository,
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

    @pytest.mark.asyncio
    async def test_should_create_entity(self, repo, session):
        """create should add a new Entity and flush."""
        name = "Test Entity"
        entity_type = EntityTypes.PERSON
        user_id = uuid4()
        raw_message_id = 1

        result = await repo.create(
            name=name,
            entity_type=entity_type,
            raw_message_id=raw_message_id,
            user_id=user_id,
        )

        assert isinstance(result, Entity)
        assert result.name == name
        assert result.entity_type == entity_type
        assert result.user_id == user_id
        assert result.raw_message_id == raw_message_id
        assert result.aliases == []
        assert result.importance_score == 0
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_create_entity_with_aliases_and_description(
        self, repo, session
    ):
        """create should accept aliases, description, and importance_score."""
        result = await repo.create(
            name="Alias Entity",
            entity_type=EntityTypes.ORGANIZATION,
            aliases=["AE", "A.E."],
            description="An entity with aliases",
            importance_score=50,
            raw_message_id=2,
            user_id=uuid4(),
        )

        assert result.aliases == ["AE", "A.E."]
        assert result.description == "An entity with aliases"
        assert result.importance_score == 50

    @pytest.mark.asyncio
    async def test_should_bulk_create_entities(self, repo, session):
        """bulk_create should insert multiple entities and return them."""
        user_id = uuid4()
        entity_dicts = [
            {
                "name": "Entity A",
                "entity_type": EntityTypes.PERSON.value,
                "aliases": [],
                "description": None,
                "importance_score": 0,
                "raw_message_id": 1,
                "user_id": user_id,
            },
            {
                "name": "Entity B",
                "entity_type": EntityTypes.ORGANIZATION.value,
                "aliases": ["B"],
                "description": None,
                "importance_score": 25,
                "raw_message_id": 1,
                "user_id": user_id,
            },
        ]

        # Mock execute to return scalars with Entity objects
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [
            Entity(
                name="Entity A",
                entity_type=EntityTypes.PERSON,
                raw_message_id=1,
                user_id=user_id,
            ),
            Entity(
                name="Entity B",
                entity_type=EntityTypes.ORGANIZATION,
                aliases=["B"],
                importance_score=25,
                raw_message_id=1,
                user_id=user_id,
            ),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.bulk_create(entity_dicts)

        assert len(result) == 2
        assert result[0].name == "Entity A"
        assert result[1].name == "Entity B"
        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_get_entity_by_id(self, repo, session):
        """get_by_id should return an Entity when found."""
        entity_id = uuid4()
        expected = Entity(
            id=entity_id,
            name="Found",
            entity_type=EntityTypes.CONCEPT,
            raw_message_id=1,
            user_id=uuid4(),
        )
        session.get = AsyncMock(return_value=expected)

        result = await repo.get_by_id(entity_id)

        assert result is not None
        assert result.id == entity_id
        assert result.name == "Found"
        session.get.assert_awaited_once_with(Entity, entity_id)

    @pytest.mark.asyncio
    async def test_should_return_none_when_entity_not_found(self, repo, session):
        """get_by_id should return None when no entity exists."""
        session.get = AsyncMock(return_value=None)

        result = await repo.get_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_should_update_entity_fields(self, repo, session):
        """update should modify fields on an Entity and flush."""
        entity = Entity(
            name="Old",
            entity_type=EntityTypes.PERSON,
            description="Old description",
            raw_message_id=1,
            user_id=uuid4(),
        )

        result = await repo.update(entity, name="New", description="New description")

        assert result.name == "New"
        assert result.description == "New description"
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_ignore_unknown_fields_on_update(self, repo, session):
        """update should silently ignore fields that don't exist on the model."""
        entity = Entity(
            name="Test",
            entity_type=EntityTypes.PERSON,
            raw_message_id=1,
            user_id=uuid4(),
        )

        result = await repo.update(entity, name="Updated", nonexistent="ignored")

        assert result.name == "Updated"
        assert not hasattr(result, "nonexistent")


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

    @pytest.mark.asyncio
    async def test_should_create_event(self, repo, session):
        """create should add a new Event and flush."""
        result = await repo.create(
            summary="Test event",
            raw_message_id=1,
            user_id=uuid4(),
        )

        assert isinstance(result, Event)
        assert result.summary == "Test event"
        assert result.importance_score == 0
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_create_event_with_timestamp(self, repo, session):
        """create should accept an optional timestamp."""
        result = await repo.create(
            summary="Timed event",
            timestamp="2024-01-15T10:00:00Z",
            importance_score=50,
            raw_message_id=2,
            user_id=uuid4(),
        )

        assert result.summary == "Timed event"
        assert result.timestamp == "2024-01-15T10:00:00Z"
        assert result.importance_score == 50

    @pytest.mark.asyncio
    async def test_should_get_event_by_id(self, repo, session):
        """get_by_id should return an Event when found."""
        event_id = uuid4()
        expected = Event(
            id=event_id,
            summary="Found event",
            raw_message_id=1,
            user_id=uuid4(),
        )
        session.get = AsyncMock(return_value=expected)

        result = await repo.get_by_id(event_id)

        assert result is not None
        assert result.id == event_id
        session.get.assert_awaited_once_with(Event, event_id)

    @pytest.mark.asyncio
    async def test_should_return_none_when_event_not_found(self, repo, session):
        """get_by_id should return None when no event exists."""
        session.get = AsyncMock(return_value=None)

        result = await repo.get_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_should_list_events_by_user(self, repo, session):
        """list_by_user should return events for a given user."""
        user_id = uuid4()
        events = [
            Event(summary="Event 1", raw_message_id=1, user_id=user_id),
            Event(summary="Event 2", raw_message_id=2, user_id=user_id),
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = events
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_by_user(user_id)

        assert len(result) == 2
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_list_events_by_user_with_pagination(self, repo, session):
        """list_by_user should respect limit and offset."""
        user_id = uuid4()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_by_user(user_id, limit=10, offset=5)

        assert result == []

    @pytest.mark.asyncio
    async def test_should_list_events_by_entity(self, repo, session):
        """list_by_entity should return events linked to a given entity."""
        entity_id = uuid4()
        events = [
            Event(summary="Related event", raw_message_id=1, user_id=uuid4()),
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = events
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_by_entity(entity_id)

        assert len(result) == 1
        assert result[0].summary == "Related event"
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_link_entity_to_event(self, repo, session):
        """link_entity should create an EventEntityRelation."""
        event_id = uuid4()
        entity_id = uuid4()

        result = await repo.link_entity(event_id=event_id, entity_id=entity_id)

        assert isinstance(result, EventEntityRelation)
        assert result.event_id == event_id
        assert result.entity_id == entity_id
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_bulk_create_events(self, repo, session):
        """bulk_create should insert multiple events."""
        user_id = uuid4()
        event_dicts = [
            {
                "summary": "Event A",
                "importance_score": 0,
                "raw_message_id": 1,
                "user_id": user_id,
            },
            {
                "summary": "Event B",
                "importance_score": 50,
                "raw_message_id": 1,
                "user_id": user_id,
            },
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [
            Event(summary="Event A", raw_message_id=1, user_id=user_id),
            Event(
                summary="Event B",
                importance_score=50,
                raw_message_id=1,
                user_id=user_id,
            ),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.bulk_create(event_dicts)

        assert len(result) == 2
        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_bulk_link_entities(self, repo, session):
        """bulk_link_entities should create multiple EventEntityRelations."""
        links = [
            {"event_id": uuid4(), "entity_id": uuid4()},
            {"event_id": uuid4(), "entity_id": uuid4()},
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [
            EventEntityRelation(
                event_id=links[0]["event_id"], entity_id=links[0]["entity_id"]
            ),
            EventEntityRelation(
                event_id=links[1]["event_id"], entity_id=links[1]["entity_id"]
            ),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.bulk_link_entities(links)

        assert len(result) == 2
        session.execute.assert_awaited_once()
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

    @pytest.mark.asyncio
    async def test_should_create_relationship(self, repo, session):
        """create should add a new RelationshipHistory."""
        from_entity_id = uuid4()
        to_entity_id = uuid4()
        user_id = uuid4()

        result = await repo.create(
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            rel_type="WORKS_FOR",
            user_id=user_id,
        )

        assert isinstance(result, RelationshipHistory)
        assert result.from_entity_id == from_entity_id
        assert result.to_entity_id == to_entity_id
        assert result.rel_type == "WORKS_FOR"
        assert result.user_id == user_id
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_bulk_create_relationships(self, repo, session):
        """bulk_create should insert multiple relationships."""
        user_id = uuid4()
        rel_dicts = [
            {
                "from_entity_id": uuid4(),
                "to_entity_id": uuid4(),
                "rel_type": "WORKS_FOR",
                "user_id": user_id,
            },
            {
                "from_entity_id": uuid4(),
                "to_entity_id": uuid4(),
                "rel_type": "FRIEND_OF",
                "user_id": user_id,
            },
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [
            RelationshipHistory(
                from_entity_id=rel_dicts[0]["from_entity_id"],
                to_entity_id=rel_dicts[0]["to_entity_id"],
                rel_type="WORKS_FOR",
                user_id=user_id,
            ),
            RelationshipHistory(
                from_entity_id=rel_dicts[1]["from_entity_id"],
                to_entity_id=rel_dicts[1]["to_entity_id"],
                rel_type="FRIEND_OF",
                user_id=user_id,
            ),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.bulk_create(rel_dicts)

        assert len(result) == 2
        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_find_relationships_by_entity(self, repo, session):
        """find_by_entity should return relationships in both directions."""
        entity_id = uuid4()
        relationships = [
            RelationshipHistory(
                from_entity_id=entity_id,
                to_entity_id=uuid4(),
                rel_type="WORKS_FOR",
                user_id=uuid4(),
            ),
            RelationshipHistory(
                from_entity_id=uuid4(),
                to_entity_id=entity_id,
                rel_type="FRIEND_OF",
                user_id=uuid4(),
            ),
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = relationships
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.find_by_entity(entity_id)

        assert len(result) == 2
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_find_relationship_between_two_entities(self, repo, session):
        """find_between should return the relationship linking two entities."""
        entity_a = uuid4()
        entity_b = uuid4()
        rel = RelationshipHistory(
            from_entity_id=entity_a,
            to_entity_id=entity_b,
            rel_type="WORKS_FOR",
            user_id=uuid4(),
        )
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [rel]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.find_between(entity_a, entity_b)

        assert len(result) == 1
        assert result[0].from_entity_id == entity_a
        assert result[0].to_entity_id == entity_b
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_find_between_reverse_order(self, repo, session):
        """find_between should work regardless of argument order."""
        entity_a = uuid4()
        entity_b = uuid4()
        rel = RelationshipHistory(
            from_entity_id=entity_b,
            to_entity_id=entity_a,
            rel_type="FRIEND_OF",
            user_id=uuid4(),
        )
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [rel]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.find_between(entity_a, entity_b)

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_should_return_empty_when_no_relationship_found(self, repo, session):
        """find_between should return empty list when no relationship exists."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.find_between(uuid4(), uuid4())

        assert result == []


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

    @pytest.mark.asyncio
    async def test_should_create_raw_message(self, repo, session):
        """create should add a new RawMessage with role and flush."""
        user_id = uuid4()

        result = await repo.create(
            content="Hello, world!",
            user_id=user_id,
            role=RawMessageRoles.USER,
        )

        assert isinstance(result, RawMessage)
        assert result.content == "Hello, world!"
        assert result.user_id == user_id
        assert result.role == RawMessageRoles.USER
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_create_assistant_raw_message(self, repo, session):
        """create should accept ASSISTANT role."""
        result = await repo.create(
            content="AI response",
            user_id=uuid4(),
            role=RawMessageRoles.ASSISTANT,
        )

        assert result.role == RawMessageRoles.ASSISTANT

    @pytest.mark.asyncio
    async def test_should_get_raw_message_by_id(self, repo, session):
        """get_by_id should return a RawMessage when found."""
        expected = RawMessage(
            id=42, content="Test", user_id=uuid4(), role=RawMessageRoles.USER
        )
        session.get = AsyncMock(return_value=expected)

        result = await repo.get_by_id(42)

        assert result is not None
        assert result.id == 42
        assert result.content == "Test"
        session.get.assert_awaited_once_with(RawMessage, 42)

    @pytest.mark.asyncio
    async def test_should_return_none_when_raw_message_not_found(self, repo, session):
        """get_by_id should return None when no message exists."""
        session.get = AsyncMock(return_value=None)

        result = await repo.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_should_list_raw_messages_by_user(self, repo, session):
        """list_by_user should return messages for a given user."""
        user_id = uuid4()
        messages = [
            RawMessage(
                id=1, content="Msg 1", user_id=user_id, role=RawMessageRoles.USER
            ),
            RawMessage(
                id=2, content="Msg 2", user_id=user_id, role=RawMessageRoles.ASSISTANT
            ),
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = messages
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.list_by_user(user_id)

        assert len(result) == 2
        session.execute.assert_awaited_once()


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

    @pytest.mark.asyncio
    async def test_should_create_embedding_with_uuid(self, repo, session):
        """create should add a new Embedding with embeddable_uuid."""
        user_id = uuid4()
        embeddable_uuid = uuid4()

        result = await repo.create(
            embeddable_uuid=embeddable_uuid,
            embeddable_type=EmbeddableType.ENTITIES,
            embedding=[0.1, 0.2, 0.3],
            model_version="test-model",
            model_provider="test-provider",
            user_id=user_id,
        )

        assert isinstance(result, Embedding)
        assert result.embeddable_uuid == embeddable_uuid
        assert result.embeddable_id is None
        assert result.embeddable_type == EmbeddableType.ENTITIES
        assert result.model_version == "test-model"
        assert result.model_provider == "test-provider"
        assert result.user_id == user_id
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_create_embedding_with_id(self, repo, session):
        """create should add a new Embedding with embeddable_id."""
        result = await repo.create(
            embeddable_id=42,
            embeddable_type=EmbeddableType.RAW_MESSAGE,
            embedding=[0.4, 0.5],
            model_version="v2",
            model_provider="provider",
            user_id=uuid4(),
        )

        assert result.embeddable_id == 42
        assert result.embeddable_uuid is None

    @pytest.mark.asyncio
    async def test_should_create_embedding_with_chunk_info(self, repo, session):
        """create should accept optional chunk_index and total_chunks."""
        result = await repo.create(
            embeddable_id=1,
            embeddable_type=EmbeddableType.ENTITIES,
            embedding=[0.1],
            model_version="v1",
            model_provider="p",
            user_id=uuid4(),
            chunk_index=0,
            total_chunks=3,
        )

        assert result.chunk_index == 0
        assert result.total_chunks == 3

    @pytest.mark.asyncio
    async def test_should_bulk_create_embeddings(self, repo, session):
        """bulk_create should insert multiple embeddings."""
        user_id = uuid4()
        embed_dicts = [
            {
                "embeddable_uuid": uuid4(),
                "embeddable_id": None,
                "embeddable_type": EmbeddableType.ENTITIES.value,
                "embedding": [0.1],
                "model_version": "v1",
                "model_provider": "p",
                "user_id": user_id,
                "chunk_index": None,
                "total_chunks": None,
            },
            {
                "embeddable_uuid": None,
                "embeddable_id": 42,
                "embeddable_type": EmbeddableType.RAW_MESSAGE.value,
                "embedding": [0.2],
                "model_version": "v1",
                "model_provider": "p",
                "user_id": user_id,
                "chunk_index": 0,
                "total_chunks": 2,
            },
        ]
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [MagicMock(), MagicMock()]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        result = await repo.bulk_create(embed_dicts)

        assert len(result) == 2
        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_search_similar_embeddings(self, repo, session):
        """search_similar should return results with similarity scores."""
        user_id = uuid4()
        mock_emb = MagicMock(spec=Embedding)
        mock_emb.embeddable_type = EmbeddableType.ENTITIES
        mock_result = MagicMock()
        mock_result.all.return_value = [(mock_emb, 0.95)]

        # We need to handle the cosine_distance mock
        # The repo creates a `distance` variable from Embedding.embedding.cosine_distance
        # Since Embedding.embedding is a column expression, we just mock execute
        session.execute = AsyncMock(return_value=mock_result)

        results = await repo.search_similar(
            query_vector=[0.1, 0.2],
            user_id=user_id,
            limit=5,
            threshold=0.7,
        )

        assert len(results) == 1
        assert results[0][1] == 0.95
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_search_similar_with_type_filter(self, repo, session):
        """search_similar should filter by embeddable_type when provided."""
        user_id = uuid4()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        results = await repo.search_similar(
            query_vector=[0.1],
            embeddable_type=EmbeddableType.EVENTS,
            user_id=user_id,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_should_delete_by_embeddable_uuid(self, repo, session):
        """delete_by_embeddable should delete embeddings by UUID."""
        embeddable_uuid = uuid4()
        emb1 = MagicMock(spec=Embedding)
        emb2 = MagicMock(spec=Embedding)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [emb1, emb2]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        await repo.delete_by_embeddable(embeddable_uuid=embeddable_uuid)

        assert session.delete.call_count == 2
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_delete_by_embeddable_id(self, repo, session):
        """delete_by_embeddable should delete embeddings by integer ID."""
        embeddable_id = 42
        emb = MagicMock(spec=Embedding)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [emb]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        session.execute = AsyncMock(return_value=mock_result)

        await repo.delete_by_embeddable(embeddable_id=embeddable_id)

        session.delete.assert_called_once_with(emb)
        session.flush.assert_awaited_once()
