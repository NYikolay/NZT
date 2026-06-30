from pydantic import BaseModel, Field

from src.domain.memory.models import EntityTypes


class ExtractedEventSchema(BaseModel):
    timestamp: str | None = Field(
        default=None,
        description=(
            "The time of the event mentioned in the context. "
            "It could be the future, the present, or the past. "
            "It all depends on the context, and you need to understand that. "
            "If you can't extract the time frame, just leave it as `None`."
        ),
        examples=[
            "Today",
            "yesterday",
            "a day ago",
            "a year ago",
            "In a week",
            "21.05.2026",
        ],
    )
    summary: str = Field(
        description=(
            "A brief description of the event. Write a description that is "
            "logically sound and relevant to the event. "
            "Don't make anything up; just provide a brief description."
        ),
        examples=[
            "A cozy party with friends, live music, and games. The highlight of the evening—"
            "a birthday cake and fireworks.",
            "A lively opening reception with the artist in attendance. "
            "The paintings sold out within the first hour.",
        ],
    )


class ExtractedEntitySchema(BaseModel):
    temp_id: int = Field(
        description=(
            "Assign a unique temporary identifier to each entity so that they "
            "can be distinguished from one another and linked together."
        ),
        examples=[1, 2, 3, 4],
    )
    name: str = Field(
        description="Canonical entity name (e.g., 'Alice', 'AcmeCorp')",
        examples=["Alice", "AcmeCorp"],
    )
    entity_type: EntityTypes = Field(
        description=(
            "Entity classification (PERSON, ORGANIZATION, etc.). "
            "Very important, use only types from the examples of this field. "
            "Don't make anything up and don't create new types."
        ),
        examples=[item.value for item in EntityTypes],
    )
    aliases: list[str] = Field(
        description=(
            "List of variant names / nicknames for this entity. "
            "Keep in mind that aliases must belong to exactly one entity; "
            "they must be logically associated with it. "
            "If a message says: 'Today I met up with Alice, whom I met on Badoo. "
            "We had a good time; I think we'll get along well. And yesterday at work, "
            "our Alice—the new hire—was fired. It's a shame, of course—she couldn't "
            "handle the job.' In this example, 'Alice' refers to different people, "
            "so you need to keep that in mind."
        ),
        examples=[["Ally", "Ali", "Liss", "Cece"]],
    )
    description: str | None = Field(
        default=None,
        description=(
            "An optional field. If possible, create a description for the entity "
            "that makes logical sense in the context of the message. "
            "If not, you don't have to create one."
        ),
    )
    events: list[ExtractedEventSchema] | None = Field(
        default=None,
        description=(
            "List of events associated with this entity. As a rule, an entity is "
            "always logically linked to an event within the context of a message, "
            "but this may not always be the case. Therefore, you need to determine "
            "which event the entity you are creating is linked to and create the "
            "corresponding event; if this is not possible, then set it to null."
        ),
    )


class ExtractedEntityRelation(BaseModel):
    from_entity_temp_id: int = Field(
        description=(
            "This field is for the ID of an entity that belongs to another entity. "
            "In other words, it is logically associated with that entity."
        ),
        examples=[
            "Based on the example above, there should be an ID for an entity named Alex here"
        ],
    )
    to_entity_temp_id: int = Field(
        description=(
            "This field is for the ID of an entity that is associated with "
            "a dependent entity in some context."
        ),
        examples=[
            "Based on the example above, there should be an ID for an entity named "
            "state-owned metal manufacturing corporation here"
        ],
    )
    rel_type: str = Field(
        description="A logical description of the relationship between entities. "
        "Examples are dynamically injected at runtime based on accepted/preset relation types.",
        examples=["WORKS_FOR", "FRIEND_OF"],
    )


class EntityRelationTypeSuggestion(BaseModel):
    name: str = Field(description="Name of new entity type")
    description: str = Field(description="Short description of new entity type")
    reasoning: str = Field(description="LLM's reasoning for suggesting this type")


class LLMExtractionResult(BaseModel):
    related_entities: list[ExtractedEntityRelation] | None = Field(
        default=None,
        description=(
            "A list of relationships between entities. "
            "Let's take an example: I got a job at a state-owned metal "
            "manufacturing corporation. I met Alex there, and he's been "
            "a big help in helping me settle in."
        ),
    )
    entities: list[ExtractedEntitySchema] | None = None
    suggestions: list[EntityRelationTypeSuggestion] | None = None
