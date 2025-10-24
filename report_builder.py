import argparse, os, glob, json, time
from src.llm_client import LLMClient
from src.config import load_config

REPORT_SYSTEM_PROMPT = (
    "You are a technical writing assistant. Write a clear, structured report that explains: "
    "problem understanding, dataset and synthetic generation, LLM workflows (chain of prompts), "
    "data processing/normalization, personality modeling (Big Five), evaluation design & metrics, "
    "results summary with key numbers, error analysis with concrete examples, limitations, and future work. "
    "Focus on clarity, evaluation, and reasoning rather than UI/UX. Use concise sections and bullet points where helpful."
)

def load_run(run_dir: str):
    metrics_path = os.path.join(run_dir, "metrics.json")
    sessions_dir = os.path.join(run_dir, "sessions")
    metrics = {}
    sessions = []
    if os.path.exists(metrics_path):
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)
    if os.path.isdir(sessions_dir):
        for p in sorted(glob.glob(os.path.join(sessions_dir, "session-*.json"))):
            with open(p, "r", encoding="utf-8") as f:
                try:
                    sessions.extend(json.load(f))
                except Exception:
                    pass
    return metrics, sessions

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="path to a run folder in outputs/runs/<timestamp>")
    ap.add_argument("--lang", choices=["en","id"], default="id")
    args = ap.parse_args()

    metrics, sessions = load_run(args.run)
    cfg = load_config()
    llm = LLMClient()

    user_prompt = (
        f"Language: {'Indonesian' if args.lang=='id' else 'English'}.\n"
        f"Context:\n- Run folder: {args.run}\n"
        f"- Metrics (JSON excerpt):\n{json.dumps(metrics, ensure_ascii=False, indent=2)[:4000]}\n"
        f"- Session logs (first few entries):\n{json.dumps(sessions[:5], ensure_ascii=False, indent=2)}\n\n"
        "Write the final report meeting the assignment requirements. Include:\n"
        "1) Overview & goals.\n"
        "2) Dataset & synthetic generation rationale (domain scientists if used).\n"
        "3) LLM workflow chain (prompts, structure, sanity checks).\n"
        "4) Data processing & normalization choices.\n"
        "5) Personality modeling (Big Five) representation & justification.\n"
        "6) Evaluation metrics and key results.\n"
        "7) Error analysis with 2–3 specific examples.\n"
        "8) Limitations & future work.\n"
        "Keep it under ~2–3 pages."
    )

    content = llm.complete_text(REPORT_SYSTEM_PROMPT, user_prompt)

    out_dir = os.path.join(args.run, "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"report-{int(time.time())}.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Saved report:", out_path)

if __name__ == "__main__":
    main()