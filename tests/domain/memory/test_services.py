"""Tests for memory domain services — EntityService, EventService, RawMessageService."""

from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from src.domain.memory.models import (
    Entity,
    EntityTypes,
    Event,
    RawMessage,
    RawMessageRoles,
)
from src.domain.memory.services import (
    EntityService,
    EventService,
    RawMessageService,
)
from src.domain.memory.schemas import RawMessageResponse
from src.domain.exceptions import EntityNotFoundError


# ---------------------------------------------------------------------------
# RawMessageService tests
# ---------------------------------------------------------------------------


class TestRawMessageService:
    """Tests for RawMessageService."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def user_id(self):
        return uuid4()

    @pytest.fixture
    def service(self, session, user_id):
        return RawMessageService(session=session, user_id=user_id)

    @pytest.mark.asyncio
    async def test_should_create_raw_message(self, service, session, user_id):
        """create_raw_message should create a RawMessage and return a response."""
        now = datetime.now(timezone.utc)
        expected_model = RawMessage(
            id=1,
            content="Test message",
            user_id=user_id,
            role=RawMessageRoles.USER,
            created_at=now,
        )
        service._repo.create = AsyncMock(return_value=expected_model)

        result = await service.create_raw_message(
            content="Test message",
            role=RawMessageRoles.USER,
        )

        assert isinstance(result, RawMessageResponse)
        assert result.id == 1
        assert result.content == "Test message"
        assert result.user_id == user_id
        service._repo.create.assert_awaited_once_with(
            content="Test message",
            user_id=user_id,
            role=RawMessageRoles.USER,
        )


# ---------------------------------------------------------------------------
# EntityService tests
# ---------------------------------------------------------------------------


class TestEntityServiceGetOrCreate:
    """Tests for EntityService.get_or_create_entity."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, session):
        return EntityService(session=session)

    @pytest.mark.asyncio
    async def test_should_create_new_entity(self, service, session):
        """get_or_create_entity should create a new entity when none exists."""
        user_id = uuid4()
        raw_message_id = 1

        # No existing entity
        service._repo.get_by_name_and_user = AsyncMock(return_value=None)

        created_entity = Entity(
            id=uuid4(),
            name="New Entity",
            entity_type=EntityTypes.PERSON,
            raw_message_id=raw_message_id,
            user_id=user_id,
        )
        service._repo.create = AsyncMock(return_value=created_entity)

        result, status = await service.get_or_create_entity(
            name="New Entity",
            entity_type=EntityTypes.PERSON,
            raw_message_id=raw_message_id,
            user_id=user_id,
        )

        assert status == "created"
        assert result.id == created_entity.id
        assert result.name == "New Entity"
        service._repo.get_by_name_and_user.assert_awaited_once_with(
            "New Entity", user_id
        )
        service._repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_should_return_existing_entity(self, service, session):
        """get_or_create_entity should return existing entity with 'already_exists'."""
        user_id = uuid4()
        entity_id = uuid4()
        existing = Entity(
            id=entity_id,
            name="Existing",
            entity_type=EntityTypes.PERSON,
            aliases=["Old"],
            raw_message_id=1,
            user_id=user_id,
        )
        service._repo.get_by_name_and_user = AsyncMock(return_value=existing)
        service._repo.create = AsyncMock()

        result, status = await service.get_or_create_entity(
            name="Existing",
            entity_type=EntityTypes.PERSON,
            raw_message_id=1,
            user_id=user_id,
        )

        assert status == "already_exists"
        assert result.id == entity_id
        assert result.name == "Existing"
        service._repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_merge_aliases_on_existing_entity(self, service, session):
        """get_or_create_entity should merge new aliases into existing entity."""
        user_id = uuid4()
        existing = Entity(
            id=uuid4(),
            name="Existing",
            entity_type=EntityTypes.PERSON,
            aliases=["OldAlias"],
            raw_message_id=1,
            user_id=user_id,
        )
        service._repo.get_by_name_and_user = AsyncMock(return_value=existing)
        service._repo.update = AsyncMock(return_value=existing)

        result, status = await service.get_or_create_entity(
            name="Existing",
            entity_type=EntityTypes.PERSON,
            aliases=["NewAlias"],
            raw_message_id=1,
            user_id=user_id,
        )

        assert status == "already_exists"
        service._repo.update.assert_awaited_once()
        # Verify merge: OldAlias + NewAlias
        update_kwargs = service._repo.update.call_args.kwargs
        assert set(update_kwargs["aliases"]) == {"OldAlias", "NewAlias"}

    @pytest.mark.asyncio
    async def test_should_update_description_if_not_set(self, service, session):
        """get_or_create_entity should set description if existing has none."""
        user_id = uuid4()
        existing = Entity(
            id=uuid4(),
            name="Existing",
            entity_type=EntityTypes.PERSON,
            description=None,
            raw_message_id=1,
            user_id=user_id,
        )
        service._repo.get_by_name_and_user = AsyncMock(return_value=existing)
        service._repo.update = AsyncMock(return_value=existing)

        await service.get_or_create_entity(
            name="Existing",
            entity_type=EntityTypes.PERSON,
            description="New description",
            raw_message_id=1,
            user_id=user_id,
        )

        # Should update description
        assert service._repo.update.call_args.kwargs["description"] == "New description"

    @pytest.mark.asyncio
    async def test_should_not_update_description_if_already_set(self, service, session):
        """get_or_create_entity should not overwrite an existing description."""
        user_id = uuid4()
        existing = Entity(
            id=uuid4(),
            name="Existing",
            entity_type=EntityTypes.PERSON,
            description="Original description",
            raw_message_id=1,
            user_id=user_id,
        )
        service._repo.get_by_name_and_user = AsyncMock(return_value=existing)
        service._repo.update = AsyncMock(return_value=existing)

        await service.get_or_create_entity(
            name="Existing",
            entity_type=EntityTypes.PERSON,
            description="New description",
            raw_message_id=1,
            user_id=user_id,
        )

        # Ensure description was NOT updated
        update_calls = service._repo.update.call_args_list
        for call in update_calls:
            assert (
                "description" not in call.kwargs
                or call.kwargs["description"] != "New description"
            )


class TestEntityServiceUpdate:
    """Tests for EntityService.update_entity."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, session):
        return EntityService(session=session)

    @pytest.mark.asyncio
    async def test_should_update_entity_fields(self, service, session):
        """update_entity should update fields and return the entity."""
        entity_id = uuid4()
        entity = Entity(
            id=entity_id,
            name="Old",
            entity_type=EntityTypes.PERSON,
            raw_message_id=1,
            user_id=uuid4(),
        )
        service._repo.get_by_id = AsyncMock(return_value=entity)

        # Mock update to actually change the name
        async def _fake_update(entity_obj, **fields):
            for key, value in fields.items():
                setattr(entity_obj, key, value)
            return entity_obj

        service._repo.update = _fake_update

        result = await service.update_entity(entity_id, name="New")

        assert result.name == "New"
        service._repo.get_by_id.assert_awaited_once_with(entity_id)

    @pytest.mark.asyncio
    async def test_should_raise_when_entity_not_found(self, service, session):
        """update_entity should raise EntityNotFoundError if missing."""
        service._repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.update_entity(uuid4(), name="New")


class TestEntityServiceMerge:
    """Tests for EntityService.merge_entities."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, session):
        return EntityService(session=session)

    @pytest.mark.asyncio
    async def test_should_merge_entities(self, service, session):
        """merge_entities should merge aliases and delete the merged entity."""
        keep_id = uuid4()
        merge_id = uuid4()
        user_id = uuid4()

        keep = Entity(
            id=keep_id,
            name="Keep",
            entity_type=EntityTypes.PERSON,
            aliases=["A"],
            raw_message_id=1,
            user_id=user_id,
        )
        merge = Entity(
            id=merge_id,
            name="Merge",
            entity_type=EntityTypes.PERSON,
            aliases=["B"],
            raw_message_id=2,
            user_id=user_id,
        )

        service._repo.get_by_id = AsyncMock(side_effect=[keep, merge])
        service._repo.update = AsyncMock(return_value=keep)

        result = await service.merge_entities(keep_id=keep_id, merge_id=merge_id)

        assert result.id == keep_id
        # Should merge aliases: A + B (the code uses list(keep_aliases | merge_aliases))
        service._repo.update.assert_awaited_once()
        update_kwargs = service._repo.update.call_args.kwargs
        assert set(update_kwargs["aliases"]) == {"A", "B"}
        session.delete.assert_awaited_once_with(merge)

    @pytest.mark.asyncio
    async def test_should_not_update_aliases_if_no_new_ones(self, service, session):
        """merge_entities should skip alias update when no new aliases."""
        keep_id = uuid4()
        merge_id = uuid4()

        keep = Entity(
            id=keep_id,
            name="Keep",
            entity_type=EntityTypes.PERSON,
            aliases=["A", "B"],
            raw_message_id=1,
            user_id=uuid4(),
        )
        merge = Entity(
            id=merge_id,
            name="Merge",
            entity_type=EntityTypes.PERSON,
            aliases=["A"],  # Subset of keep's aliases
            raw_message_id=2,
            user_id=uuid4(),
        )

        service._repo.get_by_id = AsyncMock(side_effect=[keep, merge])
        service._repo.update = AsyncMock()

        result = await service.merge_entities(keep_id=keep_id, merge_id=merge_id)

        assert result.id == keep_id
        service._repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_raise_when_keep_not_found(self, service, session):
        """merge_entities should raise EntityNotFoundError if keep is missing."""
        service._repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(EntityNotFoundError):
            await service.merge_entities(keep_id=uuid4(), merge_id=uuid4())

    @pytest.mark.asyncio
    async def test_should_raise_when_merge_not_found(self, service, session):
        """merge_entities should raise EntityNotFoundError if merge is missing."""
        service._repo.get_by_id = AsyncMock(
            side_effect=[
                Entity(
                    id=uuid4(),
                    name="Keep",
                    entity_type=EntityTypes.PERSON,
                    raw_message_id=1,
                    user_id=uuid4(),
                ),
                None,
            ]
        )

        with pytest.raises(EntityNotFoundError):
            await service.merge_entities(keep_id=uuid4(), merge_id=uuid4())


# ---------------------------------------------------------------------------
# EventService tests
# ---------------------------------------------------------------------------


class TestEventService:
    """Tests for EventService."""

    @pytest.fixture
    def session(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, session):
        return EventService(session=session)

    @pytest.mark.asyncio
    async def test_should_create_event_without_entities(self, service, session):
        """create_event should create an event without linking entities."""
        user_id = uuid4()
        created_event = Event(
            id=uuid4(),
            summary="Test event",
            raw_message_id=1,
            user_id=user_id,
        )
        service._repo.create = AsyncMock(return_value=created_event)
        service._repo.link_entity = AsyncMock()

        result = await service.create_event(
            summary="Test event",
            raw_message_id=1,
            user_id=user_id,
        )

        assert result.id == created_event.id
        assert result.summary == "Test event"
        service._repo.create.assert_awaited_once()
        service._repo.link_entity.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_create_event_with_entities(self, service, session):
        """create_event should create an event and link entities."""
        user_id = uuid4()
        event_id = uuid4()
        entity_ids = [uuid4(), uuid4()]

        created_event = Event(
            id=event_id,
            summary="Event with entities",
            raw_message_id=1,
            user_id=user_id,
        )
        service._repo.create = AsyncMock(return_value=created_event)
        service._repo.link_entity = AsyncMock()

        result = await service.create_event(
            summary="Event with entities",
            raw_message_id=1,
            entity_ids=entity_ids,
            user_id=user_id,
        )

        assert result.id == event_id
        service._repo.link_entity.assert_awaited()
        assert service._repo.link_entity.call_count == 2

    @pytest.mark.asyncio
    async def test_should_create_event_with_timestamp_and_importance(
        self, service, session
    ):
        """create_event should pass timestamp and importance_score."""
        user_id = uuid4()
        created_event = Event(
            id=uuid4(),
            summary="Important event",
            timestamp="2024-06-15T14:00:00Z",
            importance_score=85,
            raw_message_id=1,
            user_id=user_id,
        )
        service._repo.create = AsyncMock(return_value=created_event)

        result = await service.create_event(
            summary="Important event",
            timestamp="2024-06-15T14:00:00Z",
            importance_score=85,
            raw_message_id=1,
            user_id=user_id,
        )

        assert result.timestamp == "2024-06-15T14:00:00Z"
        assert result.importance_score == 85

    @pytest.mark.asyncio
    async def test_should_link_entity_to_event(self, service, session):
        """link_entity_to_event should link an existing entity to an event."""
        event_id = uuid4()
        entity_id = uuid4()
        service._repo.link_entity = AsyncMock()

        await service.link_entity_to_event(event_id=event_id, entity_id=entity_id)

        service._repo.link_entity.assert_awaited_once_with(
            event_id=event_id, entity_id=entity_id
        )
