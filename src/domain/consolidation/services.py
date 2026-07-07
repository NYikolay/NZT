"""Service for consolidating extracted LLM data into the memory graph."""

from __future__ import annotations

from typing import List
from uuid import UUID

import structlog
import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openrouter.operations import CreateEmbeddingsData
from sqlalchemy.ext.asyncio import AsyncSession

from src import settings
from src.domain.consolidation.schemas import ConsolidationResult
from src.domain.decorators import log_domain_operation
from src.domain.extraction.schemas import (
    LLMExtractionResult,
    ExtractedEntitySchema,
    ExtractedEntityRelation,
)
from src.domain.llm.services import LLMConnector
from src.domain.memory.models import Embedding, EmbeddableType, RawMessageRoles
from src.domain.memory.repositories import (
    EntityRepository,
    EventRepository,
    RelationshipHistoryRepository,
    EmbeddingRepository,
)
from src.domain.memory.schemas import EntityResponse, EventResponse
from src.domain.memory.services import RawMessageService, EntityRelationTypeService

logger = structlog.get_logger()


class ConsolidationService:
    """Handles bulk creation of entities, events, and relationships from LLM extraction results."""

    def __init__(self, session: AsyncSession, user_id: UUID):
        self.session = session
        self.user_id = user_id
        self._entity_repo = EntityRepository(session=session)
        self._event_repo = EventRepository(session=session)
        self._relationship_repo = RelationshipHistoryRepository(session=session)
        self._raw_message_service = RawMessageService(session=session, user_id=user_id)
        self._entity_rel_type_service = EntityRelationTypeService(session=session)

    @log_domain_operation("_consolidate_entities")
    async def _consolidate_entities(
        self,
        entities: List[ExtractedEntitySchema],
        user_id: UUID,
        raw_message_id: int,
    ) -> List[EntityResponse]:
        entity_dicts = []

        for entity_schema in entities:
            entity_dict = {
                "name": entity_schema.name,
                "entity_type": entity_schema.entity_type.value,
                "aliases": entity_schema.aliases or [],
                "description": entity_schema.description,
                "importance_score": 0,
                "raw_message_id": raw_message_id,
                "user_id": user_id,
            }
            entity_dicts.append(entity_dict)

        created_entities = await self._entity_repo.bulk_create(entity_dicts)

        return [EntityResponse.model_validate(entity) for entity in created_entities]

    @staticmethod
    @log_domain_operation("_extract_entity_events")
    async def _extract_entity_events(
        entities: List[ExtractedEntitySchema],
        temp_id_to_uuid: dict[int, UUID],
        raw_message_id: int,
        user_id: UUID,
    ):
        event_dicts = []
        # Track which entity (UUID) is linked to which event (by its position/index)
        # We'll match events back to entities after creation via bulk_link_entities
        entity_event_links = []  # list of dicts with entity_uuid, event_index

        for entity_schema in entities:
            if not entity_schema.events:
                continue

            entity_uuid = temp_id_to_uuid.get(entity_schema.temp_id)
            if entity_uuid is None:
                continue

            for event_schema in entity_schema.events:
                event_dict = {
                    "summary": event_schema.summary,
                    "timestamp": event_schema.timestamp,
                    "importance_score": 0,
                    "raw_message_id": raw_message_id,
                    "user_id": user_id,
                }
                event_dicts.append(event_dict)
                entity_event_links.append(
                    {
                        "entity_uuid": entity_uuid,
                        "event_index": len(event_dicts) - 1,
                    }
                )

        return event_dicts, entity_event_links

    @log_domain_operation("consolidate_entities_events")
    async def consolidate_entities_events(
        self,
        entities: List[ExtractedEntitySchema],
        temp_id_to_uuid: dict[int, UUID],
        raw_message_id: int,
        user_id: UUID,
    ) -> List[EventResponse] | None:
        event_dicts, entity_event_links = await self._extract_entity_events(
            entities, temp_id_to_uuid, raw_message_id, user_id
        )

        if event_dicts:
            created_events = await self._event_repo.bulk_create(event_dicts)

            # ── Step 4: Bulk-link events to entities ────────────────
            link_dicts = []
            for link_info in entity_event_links:
                event = created_events[link_info["event_index"]]
                link_dicts.append(
                    {
                        "entity_id": link_info["entity_uuid"],
                        "event_id": event.id,
                    }
                )

            if link_dicts:
                await self._event_repo.bulk_link_entities(link_dicts)

            logger.info(
                "events_bulk_created",
                count=len(created_events),
                links=len(link_dicts),
                user_id=str(user_id),
            )

            return [EventResponse.model_validate(event) for event in created_events]
        return None

    @log_domain_operation("consolidate_events_relationship")
    async def consolidate_events_relationship(
        self,
        related_entities: List[ExtractedEntityRelation],
        temp_id_to_uuid: dict,
        user_id: UUID,
    ):
        relationship_dicts = []
        for rel_schema in related_entities:
            from_uuid = temp_id_to_uuid.get(rel_schema.from_entity_temp_id)
            to_uuid = temp_id_to_uuid.get(rel_schema.to_entity_temp_id)

            if from_uuid is None or to_uuid is None:
                continue

            if from_uuid == to_uuid:
                continue

            relationship_dicts.append(
                {
                    "from_entity_id": from_uuid,
                    "to_entity_id": to_uuid,
                    "rel_type": rel_schema.rel_type,
                    "user_id": user_id,
                }
            )

        if relationship_dicts:
            await self._relationship_repo.bulk_create(relationship_dicts)

            logger.info(
                "relationships_bulk_created",
                count=len(relationship_dicts),
                user_id=str(user_id),
            )

    @log_domain_operation("consolidate")
    async def consolidate(
        self, *, extracted_data: LLMExtractionResult, raw_message: str
    ) -> ConsolidationResult:
        """Process an LLMExtractionResult and persist entities, events, and relationships.

        Steps:
        1. Bulk-create all entities from extracted_data.entities.
        2. Map each entity's temp_id to its actual UUID.
        3. Flatten all events across all entities and bulk-create them.
        4. Bulk-link events to their parent entities via EventEntityRelation.
        5. Bulk-create relationships from extracted_data.related_entities using
           the temp_id → UUID mapping.
        """

        # ── Raw message creation ──────────────────────────────────
        raw_message = await self._raw_message_service.create_raw_message(
            raw_message, RawMessageRoles.USER
        )
        consolidation_result = ConsolidationResult(raw_message=raw_message)

        # ── New relationship type creation ──────────────────────────────────
        if extracted_data.suggestions:
            await self._entity_rel_type_service.bulk_create_extracted_relation_types(
                extracted_data.suggestions, source_message_id=raw_message.id
            )

        # ── Bulk-create entities ──────────────────────────────────
        temp_id_to_uuid: dict[int, UUID] = {}

        if extracted_data.entities:
            created_entities = await self._consolidate_entities(
                extracted_data.entities, self.user_id, raw_message.id
            )
            consolidation_result.entities = created_entities
            # Map temp_id → actual UUID by zipping with the original order
            for entity_schema, created_entity in zip(
                extracted_data.entities, created_entities
            ):
                temp_id_to_uuid[entity_schema.temp_id] = created_entity.id

        # ── Flatten events and bulk-create them ──────────────
        if extracted_data.entities and any(e.events for e in extracted_data.entities):
            created_events = await self.consolidate_entities_events(
                extracted_data.entities, temp_id_to_uuid, raw_message.id, self.user_id
            )
            consolidation_result.events = created_events

        # ── Bulk-create relationships ─────────────────────────────
        if extracted_data.related_entities:
            await self.consolidate_events_relationship(
                extracted_data.related_entities, temp_id_to_uuid, self.user_id
            )

        return consolidation_result


class EmbeddingGeneratorService:
    """Generates and persists embeddings for consolidation results.

    Splits text into chunks, generates embeddings via LLM API,
    and persists them to the database in bulk.
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        provider: str = "openai",
        chunk_size: int = 800,
        chunk_overlap: int = 200,
        min_chunk_tokens: int = 50,
    ):
        self.model = model
        self.provider = provider
        self.llm_connector = LLMConnector(settings.OPEN_ROUTER_API_KEY)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_tokens = min_chunk_tokens
        self.separators = ["\n\n", "\n", ". ", "! ", "? ", ", ", " ", ""]
        self.splitter = RecursiveCharacterTextSplitter(
            separators=self.separators,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True,
        )
        self.encoding = tiktoken.encoding_for_model(model)

    def _tiktoken_len(self, text: str) -> int:
        return len(self.encoding.encode(text))

    @log_domain_operation("_split_text")
    async def _split_text(self, text: str) -> tuple[list[str], int]:
        token_count = self._tiktoken_len(text)

        if token_count < self.chunk_size:
            return [text], 1

        split_texts = self.splitter.split_text(text)

        chunks = []

        for i, chunk_text in enumerate(split_texts):
            token_count = self._tiktoken_len(chunk_text)

            if token_count < self.min_chunk_tokens:
                continue

            chunks.append(chunk_text)

        return chunks, len(chunks)

    @log_domain_operation("generate_embedding")
    async def generate_embedding(
        self, content: List[str]
    ) -> List[CreateEmbeddingsData]:
        embeddings = await self.llm_connector.get_llm_embedding(content=content)

        return embeddings

    @log_domain_operation("generate_consolidation_embeddings")
    async def generate_consolidation_embeddings(
        self,
        consolidation_result: ConsolidationResult,
        user_id: UUID,
        session: AsyncSession,
    ) -> List[Embedding]:
        """Generate and persist embeddings for all embeddables in a consolidation result.

        Collects text from entities, events, and raw_message, splits into chunks,
        generates embeddings via a single LLM API call, and bulk-persists them.

        Returns the list of created Embedding ORM objects.
        """
        embedding_repo = EmbeddingRepository(session=session)

        # ── Step 1: Collect all embeddable sources ──────────────────────
        # Each source: (text, embeddable_type, embeddable_uuid, embeddable_id)
        sources: list[tuple[str, EmbeddableType, UUID | None, int | None]] = []

        if consolidation_result.entities:
            for entity in consolidation_result.entities:
                sources.append(
                    (entity.canonical_text, EmbeddableType.ENTITIES, entity.id, None)
                )

        if consolidation_result.events:
            for event in consolidation_result.events:
                sources.append((event.summary, EmbeddableType.EVENTS, event.id, None))

        if consolidation_result.raw_message:
            sources.append(
                (
                    consolidation_result.raw_message.content,
                    EmbeddableType.RAW_MESSAGE,
                    None,
                    consolidation_result.raw_message.id,
                )
            )

        if not sources:
            logger.info("no_embeddable_sources", user_id=str(user_id))
            return []

        # ── Step 2: Split each source into chunks ───────────────────────
        # We build a flat list of (chunk_text, source_index, chunk_index, total_chunks)
        # and track which source each chunk belongs to.
        chunk_entries: list[dict] = []  # each: text, source_idx, chunk_idx, total

        for source_idx, (
            text,
            embeddable_type,
            embeddable_uuid,
            embeddable_id,
        ) in enumerate(sources):
            if not text or not text.strip():
                continue

            chunks, total_chunks = await self._split_text(text)

            for chunk_idx, chunk_text in enumerate(chunks):
                chunk_entries.append(
                    {
                        "text": chunk_text,
                        "source_idx": source_idx,
                        "chunk_idx": chunk_idx,
                        "total_chunks": total_chunks,
                    }
                )

        if not chunk_entries:
            logger.info("no_chunks_after_splitting", user_id=str(user_id))
            return []

        # ── Step 3: Generate embeddings for all chunks in one API call ──
        all_chunk_texts = [entry["text"] for entry in chunk_entries]
        embedding_results = await self.generate_embedding(all_chunk_texts)

        # ── Step 4: Build Embedding dicts ───────────────────────────────
        embedding_dicts: list[dict] = []

        for i, entry in enumerate(chunk_entries):
            source_idx = entry["source_idx"]
            _, embeddable_type, embeddable_uuid, embeddable_id = sources[source_idx]

            # Get the embedding vector from the API response
            # The API returns results in the same order as input
            emb_data = embedding_results[i]

            embedding_dict = {
                "embeddable_uuid": embeddable_uuid,
                "embeddable_id": embeddable_id,
                "embeddable_type": embeddable_type.value,
                "embedding": emb_data.embedding,
                "model_version": self.model,
                "model_provider": self.provider,
                "user_id": user_id,
                "chunk_index": entry["chunk_idx"]
                if entry["total_chunks"] > 1
                else None,
                "total_chunks": entry["total_chunks"]
                if entry["total_chunks"] > 1
                else None,
            }
            embedding_dicts.append(embedding_dict)

        # ── Step 5: Bulk-persist all embeddings ─────────────────────────
        created_embeddings = await embedding_repo.bulk_create(embedding_dicts)

        logger.info(
            "consolidation_embeddings_created",
            count=len(created_embeddings),
            sources=len(sources),
            user_id=str(user_id),
        )

        return created_embeddings
