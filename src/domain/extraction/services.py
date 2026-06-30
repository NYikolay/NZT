import json
import re

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.extraction.schemas import LLMExtractionResult
from src.domain.llm.services import LLMConnector
from src.domain.memory.repositories import EntityRelationTypeRepository


async def build_extraction_context(session: AsyncSession) -> list[dict]:
    """Build the system prompt with dynamic rel_type examples from the database.

    Queries EntityRelationType records where is_accepted or is_preset is True
    and injects their names as examples for the rel_type field.
    """

    # Fetch dynamic relation types from DB
    repo = EntityRelationTypeRepository(session)
    types = await repo.list_accepted_or_preset()
    relation_type_names = [t.name for t in types]

    # Fallback: if no records exist, use the enum values
    if not relation_type_names:
        from src.domain.memory.models import EntityRelationTypes

        relation_type_names = [item.value for item in EntityRelationTypes]

    # Build the full JSON schema and inject dynamic examples
    schema = LLMExtractionResult.model_json_schema()
    rel_type_schema = (
        schema.get("$defs", {})
        .get("ExtractedEntityRelation", {})
        .get("properties", {})
        .get("rel_type", {})
    )
    rel_type_schema["examples"] = relation_type_names

    return [
        {
            "role": "system",
            "content": f"""
                You are an expert in information extraction and knowledge graph construction.

                Your task is to extract structured information from the input text according to the JSON schema provided below. Try to extract as many entities and events as possible according to the rules listed below

                ## CRITICAL RULES:

                1. **Language Preservation**: Extract all text values (names, aliases, summaries, descriptions) EXACTLY as they appear in the source text. Do NOT translate, paraphrase, or modify the original language. Preserve the original wording 100%.

                2. **No Hallucination**: Use ONLY information that is explicitly stated or clearly implied in the text. Do not invent, assume, or add any details that are not present in the source.

                3. **Temp IDs**: Assign a unique integer ID to each entity (1, 2, 3, ...). These are temporary and used only for linking entities and relations within this extraction.

                4. **New entity relation types**:  Use this as a last resort. If you cannot select an existing rel_type from the examples list for an ExtractedEntityRelation, you can create a new type. Naming convention example: WORKS_FOR — all letters are uppercase, and words are separated by underscores

                ## An important point to note: if there's nothing to extract, then there's no need to do it.

                ## OUTPUT FORMAT:

                Return ONLY valid JSON that matches this exact schema. Do not include any explanations, comments, or additional text outside the JSON. Below, 
                I'll provide a JSON schema with a description of the properties to be extracted, explanations, and examples. Please use this.


                ## Json schema:

                {json.dumps(schema, indent=2)}

        """,
        }
    ]


async def extract_data(api_key: str, message: str, session: AsyncSession):
    context = await build_extraction_context(session)
    llm = LLMConnector(api_key=api_key, context_messages=context)

    extracted_message = await llm.chat_llm(message)
    clean_response = re.sub(r"```json\s*|\s*```", "", extracted_message).strip()

    return LLMExtractionResult.model_validate_json(clean_response)
