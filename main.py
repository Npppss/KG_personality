# Top-level imports (perbaikan pada impor 'src')
import argparse
import os
import time
from typing import List, Dict
from tqdm import tqdm
from src.config import load_config
from src.llm_client import LLMClient
from src.prompts import KG_EXTRACT_SYSTEM, PERSONALITY_SYSTEM, SYNTHETIC_DATA_SYSTEM
from src.models import Entity, Relation, ExtractionResult, PersonalityResult, SyntheticDoc
from src.kg_builder import KGBuilder
from src.evaluator import evaluate_extraction, evaluate_personality
from src.dagshub_tracker import DagsHubTracker
from src.normalization import canon_relation

def parse_extraction_json(j: Dict) -> ExtractionResult:
    ents, rels = [], []

    # normalize entities to a list
    raw_entities = j.get("entities", [])
    if isinstance(raw_entities, dict):
        raw_entities = list(raw_entities.values())

    for e in raw_entities:
        if isinstance(e, dict):
            name = e.get("name") or e.get("entity") or ""
            etype = e.get("type") or e.get("category") or "Concept"
        elif isinstance(e, str):
            s = e.strip()
            name, etype = s, "Concept"
            import re
            m = re.match(r"^(.*)\s*\((Person|Organization|Event|Location|Concept)\)\s*$", s)
            if m:
                name = m.group(1).strip()
                etype = m.group(2)
        else:
            continue
        if not name:
            continue
        ents.append(Entity(
            id=name.lower(),
            name=name,
            type=etype,
            canonical_name=name,
        ))

    # normalize relations to a list
    raw_relations = j.get("relations", [])
    if isinstance(raw_relations, dict):
        raw_relations = list(raw_relations.values())

    for r in raw_relations:
        if isinstance(r, dict):
            source_name = r.get("source_name") or r.get("source") or ""
            target_name = r.get("target_name") or r.get("target") or ""
            rel_type = r.get("relation_type") or r.get("type") or "MENTIONS"
            conf = r.get("confidence", 1.0)
            evidence = r.get("evidence")
        elif isinstance(r, str):
            # fallback: treat as evidence-only string
            source_name, target_name, rel_type = "", "", "MENTIONS"
            conf, evidence = 1.0, r
        else:
            continue

        rels.append(Relation(
            source_id=(source_name or "").lower(),
            target_id=(target_name or "").lower(),
            type=rel_type,
            confidence=float(conf) if isinstance(conf, (int, float, str)) else 1.0,
            evidence=evidence,
            meta={"source_name": source_name, "target_name": target_name},
        ))

    return ExtractionResult(entities=ents, relations=rels)

def parse_personality_json(j: Dict) -> PersonalityResult:
    raw_traits = j.get("traits", {})
    traits_dict = {}
    if isinstance(raw_traits, dict):
        # ensure values are floats
        traits_dict = {
            person: {trait: float(val) for trait, val in scores.items()}
            for person, scores in raw_traits.items()
        }
    elif isinstance(raw_traits, list):
        # try to coerce list-shaped outputs into the expected dict, when possible
        big5 = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
        for item in raw_traits:
            # expect either direct big5 keys with a 'person' field, or ('trait','value','person')
            person = item.get("person") or item.get("name") or item.get("subject")
            if not person:
                continue
            traits_dict.setdefault(person, {})
            # case: item carries big5 keys directly
            for k in big5:
                if k in item:
                    try:
                        traits_dict[person][k] = float(item[k])
                    except Exception:
                        pass
            # case: item has 'trait' and 'value' we can map when trait is big5
            tlabel = (item.get("trait") or "").strip().lower()
            val = item.get("value")
            if tlabel in big5 and val is not None:
                try:
                    v = float(val)
                    if v > 1:
                        v = v / 10.0  # scale 1–10 to 0–1 if needed
                    traits_dict[person][tlabel] = v
                except Exception:
                    pass
    evidence_dict = j.get("evidence", {}) if isinstance(j.get("evidence", {}), dict) else {}
    return PersonalityResult(traits=traits_dict, evidence=evidence_dict)

def post_process_relations(relations: List[Relation], entities: List[Entity]) -> List[Relation]:
    """Post-process relations to improve quality and consistency"""
    
    # Create entity name mapping for normalization
    entity_names = {}
    for e in entities:
        # Map both full and short names
        entity_names[e.name.lower()] = e.name
        
        # Handle Dr./Prof. variations
        if e.name.startswith(('Dr.', 'Prof.')):
            parts = e.name.split()
            if len(parts) >= 3:
                # Full name like "Dr. Emily Carter" -> also map "Dr. Carter"
                short_form = f"{parts[0]} {parts[-1]}"
                entity_names[short_form.lower()] = e.name
            elif len(parts) == 2:
                # Short form like "Dr. Carter" -> try to find full name
                for other_e in entities:
                    if (other_e.name.startswith(parts[0]) and 
                        other_e.name.endswith(parts[1]) and 
                        len(other_e.name.split()) > 2):
                        entity_names[e.name.lower()] = other_e.name
                        break
    
    processed_relations = []
    seen_relations = set()
    
    for rel in relations:
        # Get source and target names from meta
        source_name = rel.meta.get("source_name", "")
        target_name = rel.meta.get("target_name", "")
        
        if not source_name or not target_name:
            continue
        
        # Normalize entity names
        normalized_source = entity_names.get(source_name.lower(), source_name)
        normalized_target = entity_names.get(target_name.lower(), target_name)
        
        # Normalize relation type
        normalized_rel_type = canon_relation(rel.type)
        
        # Create relation signature for deduplication
        rel_signature = (normalized_source.lower(), normalized_rel_type, normalized_target.lower())
        
        if rel_signature in seen_relations:
            continue
        
        seen_relations.add(rel_signature)
        
        # Create improved relation
        improved_rel = Relation(
            source_id=normalized_source.lower(),
            target_id=normalized_target.lower(),
            type=normalized_rel_type,
            confidence=rel.confidence,
            evidence=rel.evidence,
            meta={
                "source_name": normalized_source,
                "target_name": normalized_target
            }
        )
        
        processed_relations.append(improved_rel)
    
    return processed_relations

def generate_synthetic(llm: LLMClient, n: int) -> List[SyntheticDoc]:
    docs = []
    for _ in tqdm(range(n), desc="Generating synthetic"):
        j = llm.complete_json(SYNTHETIC_DATA_SYSTEM, "Create a realistic 3-paragraph narrative.")
        gt = parse_extraction_json(j.get("ground_truth", {}))
        gp = parse_personality_json(j.get("ground_personality", {}))
        docs.append(SyntheticDoc(text=j.get("text",""), ground_truth=gt, ground_personality=gp))
    return docs

def run_on_text(llm: LLMClient, text: str) -> Dict:
    # naive segmentation by paragraphs
    segments = [p.strip() for p in text.split("\n") if p.strip()]
    all_ents, all_rels = [], []
    for seg in tqdm(segments, desc="Extracting KG"):
        ej = llm.complete_json(KG_EXTRACT_SYSTEM, seg)
        res = parse_extraction_json(ej)
        all_ents.extend(res.entities)
        all_rels.extend(res.relations)

    # Post-process relations to improve quality
    print(f"Before post-processing: {len(all_rels)} relations")
    all_rels = post_process_relations(all_rels, all_ents)
    print(f"After post-processing: {len(all_rels)} relations")

    # personality inference across whole document (names appear in all_ents)
    names = sorted(set([e.name for e in all_ents if e.type == "Person"]))
    pj = llm.complete_json(PERSONALITY_SYSTEM, "Infer traits for persons: " + ", ".join(names))
    pr = parse_personality_json(pj)

    # build graph
    builder = KGBuilder()
    builder.add_entities(all_ents)
    builder.add_relations(all_rels)
    builder.add_personality(pr)
    return {
        "extraction": ExtractionResult(entities=all_ents, relations=all_rels),
        "personality": pr,
        "graph": builder,
    }

def main():
    cfg = load_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["synthetic","file"], default="synthetic")
    parser.add_argument("--n", type=int, default=3, help="num synthetic docs")
    parser.add_argument("--input", type=str, help="path to input text file")
    args = parser.parse_args()

    out_base = os.path.join(cfg["out_dir"], "runs", time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(out_base, exist_ok=True)

    # Initialize DagsHub tracking
    tracker = DagsHubTracker()
    experiment_name = f"kg_personality_{args.mode}"
    run_name = f"{args.mode}_{time.strftime('%Y%m%d_%H%M%S')}"
    tracker.start_experiment(experiment_name, run_name)

    # Log pipeline parameters
    tracker.log_params({
        "mode": args.mode,
        "n_docs": args.n if args.mode == "synthetic" else 1,
        "llm_provider": cfg["llm_provider"],
        "model": cfg.get(f"{cfg['llm_provider']}_model", "unknown"),
        "temperature": cfg["temperature"],
        "input_file": args.input if args.mode == "file" else None
    })

    llm = LLMClient()

    if args.mode == "synthetic":
        tracker.log_stage("synthetic_generation", "Generating synthetic documents")
        docs = generate_synthetic(llm, args.n)
        
        tracker.log_stage("processing", "Processing documents and extracting knowledge")
        metrics = []
        total_entities = 0
        total_relations = 0
        avg_extraction_precision = 0
        avg_personality_accuracy = 0
        
        for i, d in enumerate(docs):
            r = run_on_text(llm, d.text)
            gml, html = r["graph"].export(os.path.join(out_base, "graphs"), f"doc{i}")
            m1 = evaluate_extraction(r["extraction"], d.ground_truth)
            m2 = evaluate_personality(r["personality"], d.ground_personality)
            
            # Track individual document metrics
            total_entities += len(r["extraction"].entities)
            total_relations += len(r["extraction"].relations)
            avg_extraction_precision += m1.get("precision", 0)
            avg_personality_accuracy += m2.get("accuracy", 0)
            
            metrics.append({"doc": i, "extraction": m1, "personality": m2, "graphml": gml, "html": html})
        
        # Calculate and log aggregate metrics
        avg_extraction_precision /= len(docs)
        avg_personality_accuracy /= len(docs)
        
        tracker.log_metrics({
            "total_documents": len(docs),
            "total_entities": total_entities,
            "total_relations": total_relations,
            "avg_entities_per_doc": total_entities / len(docs),
            "avg_relations_per_doc": total_relations / len(docs),
            "avg_extraction_precision": avg_extraction_precision,
            "avg_personality_accuracy": avg_personality_accuracy
        })
        
        # save metrics
        import orjson
        metrics_file = os.path.join(out_base, "metrics.json")
        with open(metrics_file, "wb") as f:
            f.write(orjson.dumps(metrics, option=orjson.OPT_INDENT_2))
        
        # Log artifacts to DagsHub
        tracker.log_artifact(metrics_file, "metrics")
        tracker.log_artifact(os.path.join(out_base, "graphs"), "graphs")
    else:
        if not args.input or not os.path.exists(args.input):
            raise FileNotFoundError("Provide --input path to an existing text file.")
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()
        r = run_on_text(llm, text)
        gml, html = r["graph"].export(os.path.join(out_base, "graphs"), "input")
        import orjson
        with open(os.path.join(out_base, "result.json"), "wb") as f:
            f.write(orjson.dumps({
                "graphml": gml, "html": html, "extraction": r["extraction"].model_dump(), "personality": r["personality"].model_dump()
            }, option=orjson.OPT_INDENT_2))

    # save session logs for sharing
    sess_path = llm.save_session(os.path.join(out_base, "sessions"))
    
    # Log model and session info to DagsHub
    tracker.log_model_info({
        "provider": cfg["llm_provider"],
        "model": cfg.get(f"{cfg['llm_provider']}_model", "unknown"),
        "temperature": cfg["temperature"],
        "total_api_calls": len(llm.session_logs)
    })
    
    # Log session artifacts
    tracker.log_artifact(sess_path, "session_logs")
    tracker.log_artifact(out_base, "pipeline_outputs")
    
    # Upload to DagsHub storage bucket
    experiment_name = f"{args.mode}_{time.strftime('%Y%m%d_%H%M%S')}"
    storage_success = tracker.upload_experiment_to_storage(out_base, experiment_name)
    
    if storage_success:
        print("✅ Experiment artifacts uploaded to DagsHub storage bucket")
    else:
        print("⚠️  Storage upload skipped (not configured or failed)")
    
    # End experiment
    tracker.end_experiment()
    
    print("Session logs:", sess_path)
    print("Outputs dir:", out_base)
    print("DagsHub experiment completed. Check your DagsHub repository for tracking details.")
    if storage_success:
        print("Storage bucket: https://dagshub.com/Npppss/KG_personality/src/main/experiments/")

if __name__ == "__main__":
    main()