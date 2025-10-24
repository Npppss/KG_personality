from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class Entity(BaseModel):
    id: str
    name: str
    type: str  # Person, Organization, Event, Location, Concept
    canonical_name: Optional[str] = None
    attributes: Dict[str, float] = Field(default_factory=dict)  # traits etc.
    meta: Dict[str, str] = Field(default_factory=dict)

class Relation(BaseModel):
    source_id: str
    target_id: str
    type: str
    confidence: float = 1.0
    evidence: Optional[str] = None
    meta: Dict[str, str] = Field(default_factory=dict)

class ExtractionResult(BaseModel):
    entities: List[Entity] = Field(default_factory=list)
    relations: List[Relation] = Field(default_factory=list)

class PersonalityResult(BaseModel):
    traits: Dict[str, Dict[str, float]] = Field(default_factory=dict)  # name -> {trait:score}
    evidence: Dict[str, str] = Field(default_factory=dict)  # name -> quote/justification

class SyntheticDoc(BaseModel):
    text: str
    ground_truth: ExtractionResult
    ground_personality: PersonalityResult