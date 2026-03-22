from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class EntityType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    GEOPOLITICAL = "geopolitical"
    ASSET = "asset"  # Vessel, Aircraft, Wallet, Ticker
    EVENT = "event"
    WEAPON = "weapon"

class Entity(BaseModel):
    name: str = Field(..., description="Standardized name of the entity")
    type: EntityType
    metadata: dict = Field(default_factory=dict, description="Additional info (e.g., country code, stock ticker, ICAO code)")

class RelationshipType(str, Enum):
    MENTIONS = "mentions"
    LOCATED_IN = "located_in"
    OWNED_BY = "owned_by"
    PART_OF = "part_of"
    ATTACKED = "attacked"
    TRANSFERRED_TO = "transferred_to"
    OPERATES = "operates"

class Relationship(BaseModel):
    source_id: str  # Entity name or Item ID
    target_id: str
    type: RelationshipType
    confidence: float = 1.0

class OntologyMapper:
    """Standardizes entities and relationships for the Knowledge Graph."""

    def extract_from_tags(self, tags: List[str]) -> List[Entity]:
        """Convert simple string tags into typed Entities where possible."""
        entities = []
        for tag in tags:
            # Basic heuristic mapping for now, can be improved with AI
            # tags like "country:US", "ticker:AAPL", "vessel:NAME"
            if ":" in tag:
                prefix, val = tag.split(":", 1)
                prefix = prefix.lower()
                if prefix == "country":
                    entities.append(Entity(name=val, type=EntityType.LOCATION))
                elif prefix == "ticker":
                    entities.append(Entity(name=val, type=EntityType.ASSET, metadata={"subtype": "stock_ticker"}))
                elif prefix in ["vessel", "imo", "mmsi", "icao", "tail_number"]:
                    entities.append(Entity(name=val, type=EntityType.ASSET, metadata={"subtype": prefix}))
                else:
                    entities.append(Entity(name=val, type=EntityType.EVENT))
            else:
                entities.append(Entity(name=tag, type=EntityType.EVENT))
        return entities

    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from raw text using simple heuristics (for now)."""
        entities = []
        # Simple strategy: look for capitalized words as potential entities
        words = text.split()
        for word in words:
            word = word.strip(".,;:!?()[]\"'")
            if len(word) > 3 and any(c.isupper() for c in word):
                entities.append(Entity(name=word, type=EntityType.ORGANIZATION))
        
        return self.consolidate_entities(entities)

    def consolidate_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicates and standardize names."""
        unique = {}
        for ent in entities:
            key = (ent.name.lower(), ent.type)
            if key not in unique:
                unique[key] = ent
        return list(unique.values())
