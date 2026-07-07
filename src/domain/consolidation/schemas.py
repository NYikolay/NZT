from typing import List

from pydantic import BaseModel

from src.domain.memory.schemas import RawMessageResponse, EntityResponse, EventResponse


class ConsolidationResult(BaseModel):
    raw_message: RawMessageResponse
    entities: List[EntityResponse] | None = None
    events: List[EventResponse] | None = None
