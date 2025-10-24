import os
from dotenv import load_dotenv

def load_config():
    load_dotenv()
    return {
        "llm_provider": os.getenv("LLM_PROVIDER", "openai"),  # openai or gemini
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "gemini_model": os.getenv("GEMINI_MODEL", "gemini-pro"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.2")),
        "out_dir": os.getenv("OUT_DIR", "c:\\Assigment\\outputs"),
        # DagsHub configuration
        "dagshub_enabled": os.getenv("DAGSHUB_ENABLED", "false").lower() == "true",
        "dagshub_repo": os.getenv("DAGSHUB_REPO", ""),  # username/repo-name
        "dagshub_token": os.getenv("DAGSHUB_TOKEN", ""),
        "mlflow_tracking_uri": os.getenv("MLFLOW_TRACKING_URI", ""),
        
        # DagsHub Storage Bucket Configuration
        "dagshub_bucket_name": os.getenv("DAGSHUB_BUCKET_NAME", ""),
        "dagshub_endpoint_url": os.getenv("DAGSHUB_ENDPOINT_URL", ""),
        "dagshub_access_key_id": os.getenv("DAGSHUB_ACCESS_KEY_ID", ""),
        "dagshub_region": os.getenv("DAGSHUB_REGION", "us-east-1"),
    }