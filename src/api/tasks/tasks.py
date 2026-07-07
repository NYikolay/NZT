from uuid import UUID

from src.api.dependencies import provide_transaction_taskiq
from src.core.tkq import broker
from taskiq import TaskiqDepends
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.extraction.schemas import LLMExtractionResult
from src.domain.consolidation.services import (
    ConsolidationService,
    EmbeddingGeneratorService,
)


@broker.task
async def consolidate_extracted_memory(
    user_id: UUID,
    raw_message: str,
    extracted_message_data: LLMExtractionResult,
    session: AsyncSession = TaskiqDepends(provide_transaction_taskiq),
):
    consolidation_service = ConsolidationService(session=session, user_id=user_id)
    consolidation_result = await consolidation_service.consolidate(
        extracted_data=extracted_message_data, raw_message=raw_message
    )

    embedding_service = EmbeddingGeneratorService()
    await embedding_service.generate_consolidation_embeddings(
        consolidation_result, user_id, session
    )
