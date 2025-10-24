from typing import Dict, Tuple, Set
from .models import ExtractionResult, PersonalityResult

def normalize_entity_name(name: str) -> str:
    """Normalize entity names to handle variations like 'Dr. Carter' vs 'Dr. Emily Carter'"""
    name = name.strip()
    
    # Create mapping for common name variations
    # If it's a short form like "Dr. Carter", try to match with full names
    if name.count(' ') == 1 and (name.startswith('Dr.') or name.startswith('Prof.')):
        # This is a short form like "Dr. Carter"
        return name
    
    # For full names, also create a short form mapping
    if name.count(' ') >= 2 and (name.startswith('Dr.') or name.startswith('Prof.')):
        # This is a full name like "Dr. Emily Carter"
        parts = name.split()
        if len(parts) >= 3:
            # Create short form: "Dr. Carter"
            short_form = f"{parts[0]} {parts[-1]}"
            return name  # Return full name as primary, but we'll handle matching below
    
    return name

def create_name_variants(name: str) -> Set[str]:
    """Create all possible variants of a name for matching"""
    variants = {name.strip()}
    name = name.strip()
    
    # Handle Dr./Prof. variations
    if name.startswith('Dr.') or name.startswith('Prof.'):
        parts = name.split()
        if len(parts) >= 3:
            # Full name like "Dr. Emily Carter" -> also add "Dr. Carter"
            short_form = f"{parts[0]} {parts[-1]}"
            variants.add(short_form)
        elif len(parts) == 2:
            # Short form like "Dr. Carter" -> keep as is
            pass
    
    # Add version without title
    if name.startswith('Dr.') or name.startswith('Prof.'):
        without_title = ' '.join(name.split()[1:])
        variants.add(without_title)
    
    return variants

def names_match(name1: str, name2: str) -> bool:
    """Check if two names refer to the same entity"""
    variants1 = create_name_variants(name1)
    variants2 = create_name_variants(name2)
    return bool(variants1 & variants2)

def prf(pred_set, gold_set) -> Tuple[float, float, float]:
    tp = len(pred_set & gold_set)
    fp = len(pred_set - gold_set)
    fn = len(gold_set - pred_set)
    precision = tp / (tp + fp + 1e-9)
    recall = tp / (tp + fn + 1e-9)
    f1 = 2 * precision * recall / (precision + recall + 1e-9)
    return precision, recall, f1

def evaluate_extraction(pred: ExtractionResult, gold: ExtractionResult):
    # Entity evaluation with name normalization
    pred_entities = set()
    for e in pred.entities:
        for variant in create_name_variants(e.name):
            pred_entities.add((variant, e.type))
    
    gold_entities = set()
    for e in gold.entities:
        for variant in create_name_variants(e.name):
            gold_entities.add((variant, e.type))
    
    pe, re, fe = prf(pred_entities, gold_entities)

    # Relation evaluation with fuzzy name matching
    pred_relations = []
    for r in pred.relations:
        source_name = getattr(r, "meta", {}).get("source_name", r.source_id)
        target_name = getattr(r, "meta", {}).get("target_name", r.target_id)
        pred_relations.append((source_name, r.type, target_name))
    
    gold_relations = []
    for r in gold.relations:
        source_name = getattr(r, "meta", {}).get("source_name", r.source_id)
        target_name = getattr(r, "meta", {}).get("target_name", r.target_id)
        gold_relations.append((source_name, r.type, target_name))
    
    # Fuzzy matching for relations
    matched_pred = set()
    matched_gold = set()
    
    for i, (pred_src, pred_rel, pred_tgt) in enumerate(pred_relations):
        for j, (gold_src, gold_rel, gold_tgt) in enumerate(gold_relations):
            if (pred_rel == gold_rel and 
                names_match(pred_src, gold_src) and 
                names_match(pred_tgt, gold_tgt)):
                matched_pred.add(i)
                matched_gold.add(j)
                break
    
    tp = len(matched_pred)
    fp = len(pred_relations) - tp
    fn = len(gold_relations) - len(matched_gold)
    
    pr = tp / (tp + fp + 1e-9)
    rr = tp / (tp + fn + 1e-9)
    fr = 2 * pr * rr / (pr + rr + 1e-9)

    return {
        "entities": {"precision": pe, "recall": re, "f1": fe},
        "relations": {"precision": pr, "recall": rr, "f1": fr},
    }

def evaluate_personality(pred: PersonalityResult, gold: PersonalityResult):
    import math
    people = set(pred.traits.keys()) & set(gold.traits.keys())
    if not people:
        return {"mae": None, "mse": None}
    maes, mses = [], []
    for p in people:
        for trait in ["openness","conscientiousness","extraversion","agreeableness","neuroticism"]:
            pv = float(pred.traits[p].get(trait, 0.5))
            gv = float(gold.traits[p].get(trait, 0.5))
            maes.append(abs(pv - gv))
            mses.append((pv - gv) ** 2)
    mae = sum(maes) / len(maes)
    mse = sum(mses) / len(mses)
    return {"mae": mae, "mse": mse}