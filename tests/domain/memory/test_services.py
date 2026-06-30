"""Tests for memory domain services — EntityService and EventService."""

from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from src.domain.memory.models import (
    Entity,
    EntityTypes,
    Event,
    EventEntityRelation,
)
from src.domain.memory.services import EntityService, EventService
from src.domain.exceptions import EntityNotFoundError


# ---------------------------------------------------------------------------
# EntityService tests
# ---------------------------------------------------------------------------


class TestGetOrCreateEntity:
    """Tests for EntityService.get_or_create_entity."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return EntityService(session=mock_session)

    @pytest.mark.asyncio
    async def test_should_create_new_entity_when_not_exists(
        self, service, mock_session
    ):
        """When no entity with the same name exists, create a new one."""
        user_id = uuid4()
        entity_id = uuid4()

        # Mock the repository's get_by_name_and_user to return None
        service._repo.get_by_name_and_user = AsyncMock(return_value=None)

        # Mock the repository's create to return a new entity
        async def _fake_create(**kwargs):
            return Entity(
                id=entity_id,
                name=kwargs["name"],
                entity_type=kwargs["entity_type"],
                aliases=kwargs.get("aliases") or [],
                description=kwargs.get("description"),
                importance_score=kwargs.get("importance_score", 0),
                raw_message_id=kwargs["raw_message_id"],
                user_id=kwargs["user_id"],
            )

        service._repo.create = _fake_create

        entity, status = await service.get_or_create_entity(
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
        assert status == "created"

    @pytest.mark.asyncio
    async def test_should_return_existing_entity_when_found(
        self, service, mock_session
    ):
        """When an entity with the same name exists, return it with 'already_exists'."""
        user_id = uuid4()
        entity_id = uuid4()
        existing = Entity(
            id=entity_id,
            name="Alice",
            entity_type=EntityTypes.PERSON,
            aliases=["Ali"],
            description="A person",
            importance_score=50,
            raw_message_id=1,
            user_id=user_id,
        )

        service._repo.get_by_name_and_user = AsyncMock(return_value=existing)
        service._repo.update = AsyncMock(return_value=existing)

        entity, status = await service.get_or_create_entity(
            name="Alice",
            entity_type=EntityTypes.PERSON,
            raw_message_id=2,
            user_id=user_id,
        )

        assert entity.id == entity_id
        assert entity.name == "Alice"
        assert status == "already_exists"

    @pytest.mark.asyncio
    async def test_should_merge_aliases_when_entity_exists(self, service, mock_session):
        """When entity exists, new aliases should be merged with existing ones."""
        user_id = uuid4()
        existing = Entity(
            id=uuid4(),
            name="AcmeCorp",
            entity_type=EntityTypes.ORGANIZATION,
            aliases=["ACME"],
            raw_message_id=1,
            user_id=user_id,
        )

        service._repo.get_by_name_and_user = AsyncMock(return_value=existing)
        service._repo.update = AsyncMock(return_value=existing)

        entity, status = await service.get_or_create_entity(
            name="AcmeCorp",
            entity_type=EntityTypes.ORGANIZATION,
            aliases=["Acme Inc.", "ACME"],  # ACME is duplicate, Acme Inc. is new
            raw_message_id=2,
            user_id=user_id,
        )

        assert status == "already_exists"
        # update should have been called with merged aliases
        service._repo.update.assert_called_once()
        call_kwargs = service._repo.update.call_args[1]
        assert "aliases" in call_kwargs
        merged = set(call_kwargs["aliases"])
        assert merged == {"ACME", "Acme Inc."}

    @pytest.mark.asyncio
    async def test_should_update_description_when_missing(self, service, mock_session):
        """When entity exists without description, set it from new data."""
        user_id = uuid4()
        existing = Entity(
            id=uuid4(),
            name="Bob",
            entity_type=EntityTypes.PERSON,
            description=None,
            raw_message_id=1,
            user_id=user_id,
        )

        service._repo.get_by_name_and_user = AsyncMock(return_value=existing)
        service._repo.update = AsyncMock(return_value=existing)

        entity, status = await service.get_or_create_entity(
            name="Bob",
            entity_type=EntityTypes.PERSON,
            description="Updated description",
            raw_message_id=2,
            user_id=user_id,
        )

        assert status == "already_exists"
        service._repo.update.assert_called_once_with(
            existing, description="Updated description"
        )

    @pytest.mark.asyncio
    async def test_should_not_update_description_when_already_set(
        self, service, mock_session
    ):
        """When entity already has a description, don't overwrite it."""
        user_id = uuid4()
        existing = Entity(
            id=uuid4(),
            name="Bob",
            entity_type=EntityTypes.PERSON,
            description="Original description",
            raw_message_id=1,
            user_id=user_id,
        )

        service._repo.get_by_name_and_user = AsyncMock(return_value=existing)
        service._repo.update = AsyncMock(return_value=existing)

        entity, status = await service.get_or_create_entity(
            name="Bob",
            entity_type=EntityTypes.PERSON,
            description="New description",
            raw_message_id=2,
            user_id=user_id,
        )

        assert status == "already_exists"
        # update should NOT have been called for description
        for call_args in service._repo.update.call_args_list:
            kwargs = call_args[1] if len(call_args) > 1 else {}
            assert "description" not in kwargs or kwargs["description"] is None

    @pytest.mark.asyncio
    async def test_should_not_merge_aliases_when_no_new_ones(
        self, service, mock_session
    ):
        """When no new aliases provided, don't call update."""
        user_id = uuid4()
        existing = Entity(
            id=uuid4(),
            name="Alice",
            entity_type=EntityTypes.PERSON,
            aliases=["Ali"],
            raw_message_id=1,
            user_id=user_id,
        )

        service._repo.get_by_name_and_user = AsyncMock(return_value=existing)
        # Mock update to track calls
        service._repo.update = AsyncMock(return_value=existing)

        entity, status = await service.get_or_create_entity(
            name="Alice",
            entity_type=EntityTypes.PERSON,
            raw_message_id=2,
            user_id=user_id,
        )

        assert status == "already_exists"
        # update should not have been called (no new aliases, no description to set)
        service._repo.update.assert_not_called()


class TestUpdateEntity:
    """Tests for EntityService.update_entity."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return EntityService(session=mock_session)

    @pytest.mark.asyncio
    async def test_should_update_entity_fields(self, service, mock_session):
        """Should update entity fields and return the updated entity."""
        entity_id = uuid4()
        entity = Entity(
            id=entity_id,
            name="OldName",
            entity_type=EntityTypes.PERSON,
            raw_message_id=1,
            user_id=uuid4(),
        )

        service._repo.get_by_id = AsyncMock(return_value=entity)

        # Mock update to return a copy with the new name
        async def _fake_update(entity_obj, **fields):
            for key, value in fields.items():
                if hasattr(entity_obj, key):
                    setattr(entity_obj, key, value)
            return entity_obj

        service._repo.update = _fake_update

        result = await service.update_entity(entity_id, name="NewName")

        assert result.name == "NewName"

    @pytest.mark.asyncio
    async def test_should_raise_when_entity_not_found(self, service, mock_session):
        """Should raise EntityNotFoundError when entity doesn't exist."""
        service._repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.update_entity(uuid4(), name="NewName")


class TestMergeEntities:
    """Tests for EntityService.merge_entities."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return EntityService(session=mock_session)

    @pytest.mark.asyncio
    async def test_should_merge_entities_and_delete_duplicate(
        self, service, mock_session
    ):
        """Should merge aliases from merge entity into keep entity and delete merge."""
        user_id = uuid4()
        keep_id = uuid4()
        merge_id = uuid4()

        keep = Entity(
            id=keep_id,
            name="Alice",
            entity_type=EntityTypes.PERSON,
            aliases=["Ali"],
            raw_message_id=1,
            user_id=user_id,
        )
        merge = Entity(
            id=merge_id,
            name="Alice",
            entity_type=EntityTypes.PERSON,
            aliases=["Alias", "Nickname"],
            raw_message_id=2,
            user_id=user_id,
        )

        service._repo.get_by_id = AsyncMock(side_effect=[keep, merge])
        service._repo.update = AsyncMock(return_value=keep)

        result = await service.merge_entities(keep_id=keep_id, merge_id=merge_id)

        assert result.id == keep_id
        # update should have been called with merged aliases
        service._repo.update.assert_called_once()
        call_kwargs = service._repo.update.call_args[1]
        merged_aliases = set(call_kwargs["aliases"])
        assert merged_aliases == {"Ali", "Alias", "Nickname"}
        # merge entity should have been deleted
        mock_session.delete.assert_called_once_with(merge)

    @pytest.mark.asyncio
    async def test_should_raise_when_keep_not_found(self, service, mock_session):
        """Should raise EntityNotFoundError when keep entity doesn't exist."""
        service._repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.merge_entities(keep_id=uuid4(), merge_id=uuid4())

    @pytest.mark.asyncio
    async def test_should_raise_when_merge_not_found(self, service, mock_session):
        """Should raise EntityNotFoundError when merge entity doesn't exist."""
        keep_id = uuid4()
        keep = Entity(
            id=keep_id,
            name="Alice",
            entity_type=EntityTypes.PERSON,
            raw_message_id=1,
            user_id=uuid4(),
        )

        service._repo.get_by_id = AsyncMock(side_effect=[keep, None])

        with pytest.raises(EntityNotFoundError):
            await service.merge_entities(keep_id=keep_id, merge_id=uuid4())

    @pytest.mark.asyncio
    async def test_should_not_update_when_no_new_aliases(self, service, mock_session):
        """When merge entity has no new aliases, skip update."""
        user_id = uuid4()
        keep_id = uuid4()
        merge_id = uuid4()

        keep = Entity(
            id=keep_id,
            name="Alice",
            entity_type=EntityTypes.PERSON,
            aliases=["Ali"],
            raw_message_id=1,
            user_id=user_id,
        )
        merge = Entity(
            id=merge_id,
            name="Alice",
            entity_type=EntityTypes.PERSON,
            aliases=["Ali"],  # same aliases
            raw_message_id=2,
            user_id=user_id,
        )

        service._repo.get_by_id = AsyncMock(side_effect=[keep, merge])
        # Mock update to track calls
        service._repo.update = AsyncMock(return_value=keep)

        result = await service.merge_entities(keep_id=keep_id, merge_id=merge_id)

        assert result.id == keep_id
        # update should not have been called (no new aliases)
        service._repo.update.assert_not_called()
        mock_session.delete.assert_called_once_with(merge)


# ---------------------------------------------------------------------------
# EventService tests
# ---------------------------------------------------------------------------


class TestCreateEvent:
    """Tests for EventService.create_event."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return EventService(session=mock_session)

    @pytest.mark.asyncio
    async def test_should_create_event_without_entities(self, service, mock_session):
        """Should create an event without linking any entities."""
        user_id = uuid4()
        event_id = uuid4()

        async def _fake_create(**kwargs):
            return Event(
                id=event_id,
                summary=kwargs["summary"],
                importance_score=kwargs.get("importance_score", 0),
                raw_message_id=kwargs["raw_message_id"],
                user_id=kwargs["user_id"],
            )

        service._repo.create = _fake_create

        event = await service.create_event(
            summary="Meeting with Alice",
            importance_score=50,
            raw_message_id=1,
            user_id=user_id,
        )

        assert isinstance(event, Event)
        assert event.id == event_id
        assert event.summary == "Meeting with Alice"
        assert event.importance_score == 50
        assert event.raw_message_id == 1
        assert event.user_id == user_id

    @pytest.mark.asyncio
    async def test_should_create_event_with_entity_links(self, service, mock_session):
        """Should create an event and link it to specified entities."""
        user_id = uuid4()
        event_id = uuid4()
        entity_ids = [uuid4(), uuid4()]

        async def _fake_create(**kwargs):
            return Event(
                id=event_id,
                summary=kwargs["summary"],
                raw_message_id=kwargs["raw_message_id"],
                user_id=kwargs["user_id"],
            )

        service._repo.create = _fake_create
        service._repo.link_entity = AsyncMock()

        event = await service.create_event(
            summary="Team meeting",
            raw_message_id=1,
            entity_ids=entity_ids,
            user_id=user_id,
        )

        assert event.id == event_id
        assert event.summary == "Team meeting"
        # Should have linked both entities
        assert service._repo.link_entity.call_count == 2
        service._repo.link_entity.assert_any_call(
            event_id=event_id, entity_id=entity_ids[0]
        )
        service._repo.link_entity.assert_any_call(
            event_id=event_id, entity_id=entity_ids[1]
        )

    @pytest.mark.asyncio
    async def test_should_create_event_with_timestamp(self, service, mock_session):
        """Should create an event with an optional timestamp."""
        user_id = uuid4()

        async def _fake_create(**kwargs):
            return Event(
                id=uuid4(),
                summary=kwargs["summary"],
                timestamp=kwargs.get("timestamp"),
                raw_message_id=kwargs["raw_message_id"],
                user_id=kwargs["user_id"],
            )

        service._repo.create = _fake_create

        event = await service.create_event(
            summary="Dated event",
            timestamp="2024-01-01T00:00:00Z",
            raw_message_id=1,
            user_id=user_id,
        )

        assert event.timestamp == "2024-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_should_create_event_with_empty_entity_ids(
        self, service, mock_session
    ):
        """Should create an event with empty entity_ids list (no linking)."""
        user_id = uuid4()

        async def _fake_create(**kwargs):
            return Event(
                id=uuid4(),
                summary=kwargs["summary"],
                raw_message_id=kwargs["raw_message_id"],
                user_id=kwargs["user_id"],
            )

        service._repo.create = _fake_create
        # Mock link_entity to track calls
        service._repo.link_entity = AsyncMock()

        event = await service.create_event(
            summary="Event with empty list",
            raw_message_id=1,
            entity_ids=[],
            user_id=user_id,
        )

        assert event.summary == "Event with empty list"
        service._repo.link_entity.assert_not_called()


class TestLinkEntityToEvent:
    """Tests for EventService.link_entity_to_event."""

    @pytest.fixture
    def mock_session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_session):
        return EventService(session=mock_session)

    @pytest.mark.asyncio
    async def test_should_link_entity_to_event(self, service, mock_session):
        """Should create a link between an entity and an event."""
        event_id = uuid4()
        entity_id = uuid4()
        expected_relation = EventEntityRelation(event_id=event_id, entity_id=entity_id)
        service._repo.link_entity = AsyncMock(return_value=expected_relation)

        result = await service.link_entity_to_event(
            event_id=event_id, entity_id=entity_id
        )

        assert isinstance(result, EventEntityRelation)
        assert result.event_id == event_id
        assert result.entity_id == entity_id
        service._repo.link_entity.assert_awaited_once_with(
            event_id=event_id, entity_id=entity_id
        )
